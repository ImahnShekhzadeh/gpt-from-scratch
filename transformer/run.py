"""
Run transformer.
"""
import logging
import os
import sys
from argparse import Namespace
from datetime import datetime as dt

import torch
from dataset import DictDataset
from scheduler import LRScheduler
from torch import multiprocessing as mp
from torch import optim
from torch.nn.parallel import DistributedDataParallel as DDP
from torchinfo import summary
from utils import (
    check_accuracy,
    cleanup,
    get_dataloaders,
    get_datasets_and_tokenizer,
    load_checkpoint,
    log_parameter_table,
    retrieve_args,
    save_checkpoint,
    setup,
    train_and_validate,
)

import wandb
from architecture.models import Transformer
from options import get_parser


def main(
    rank: int | torch.device,
    world_size: int,
    args: Namespace,
) -> None:
    """
    Main function.

    Args:
        rank: rank of the current process
        world_size: number of processes
        args: command line arguments
    """

    if args.seed_number is not None:
        torch.manual_seed(args.seed_number)

    if args.use_ddp:
        setup(
            rank=rank,
            world_size=world_size,
        )

    # get ids stored in dict (both for the source and target) for train, val
    # and test datasets, as well as the tokenizer
    (
        train__dict_ids,
        val__dict_ids,
        test__dict_ids,
        tokenizer,
    ) = get_datasets_and_tokenizer(
        seq_length=args.seq_length,
        tokenizer_file=args.tokenizer_file,
        vocab_size=args.vocab_size,
        min_frequency=args.min_frequency,
    )

    # convert to datasets
    train_set, val_set, test_set = (
        DictDataset(train__dict_ids),
        DictDataset(val__dict_ids),
        DictDataset(test__dict_ids),
    )

    # get dataloaders
    train_loader, val_loader, test_loader = get_dataloaders(
        train_dataset=train_set,
        val_dataset=val_set,
        test_dataset=test_set,
        batch_size=args.batch_size,
        num_workers=args.num_workers,
        pin_memory=args.pin_memory,
        use_ddp=args.use_ddp,
    )

    # get pad token ID
    pad_token_id = tokenizer.token_to_id("[PAD]")
    assert (
        pad_token_id is not None
    ), "Pad token ID not found. Please use another tokenizer."

    # define transformer
    model = Transformer(
        num__encoder_layers=args.num__encoder_layers,
        num__decoder_layers=args.num__decoder_layers,
        embedding_dim=args.embedding_dim,
        num_heads=args.num_heads,
        vocab_size=tokenizer.get_vocab_size(),
        seq_length=args.seq_length,
        dim_feedfwd=args.dim_feedfwd,
    )
    model.to(rank)
    if args.use_ddp:
        model = DDP(model, device_ids=[rank])

    # setup Weights & Biases, print # data and log parameter table
    if rank in [0, torch.device("cpu")]:
        wandb_logging = args.wandb__api_key is not None
        if wandb_logging:
            wandb.login(key=args.wandb__api_key)
            wandb.init(project="transformer")

        # TODO: print # train, val and test tokens
        logging.info(
            f"Pad token ID: {pad_token_id}\n# Train:val:test sentences: "
            f"{len(train_loader.dataset)}:{len(val_loader.dataset)}"
            f":{len(test_loader.dataset)}\n"
        )
        log_parameter_table(model)
    else:
        wandb_logging = False

    # compile model if specified
    if args.compile_mode is not None:
        logging.info(f"\nCompiling model in ``{args.compile_mode}`` mode...\n")
        model = torch.compile(model, mode=args.compile_mode, fullgraph=False)

    # Optimizer:
    optimizer = optim.Adam(
        params=model.parameters(),
        lr=1e-3,
        betas=(0.9, 0.999),
        eps=1e-08,
    )

    # Set network to train mode:
    model.train()

    if args.loading_path is not None:
        if rank == torch.device("cpu"):
            map_location = {"cuda:0": "cpu"}
        else:
            map_location = {"cuda:0": f"cuda:{rank}"}

        load_checkpoint(
            model=model,
            optimizer=optimizer,
            checkpoint=torch.load(
                args.loading_path, map_location=map_location
            ),
        )

    # Train the network:
    lr_scheduler = LRScheduler(
        optimizer=optimizer,
        d_model=args.embedding_dim,
        warmup_steps=args.warmup_steps,
        lr_multiplier=args.lr_multiplier,
    )
    checkpoint = train_and_validate(
        pad_token_id=pad_token_id,
        model=model,
        optimizer=optimizer,
        num_epochs=args.num_epochs,
        rank=rank,
        use_amp=args.use_amp,
        train_loader=train_loader,
        val_loader=val_loader,
        lr_scheduler=lr_scheduler,
        freq_output__train=args.freq_output__train,
        freq_output__val=args.freq_output__val,
        max_norm=args.max_norm,
        world_size=world_size,
        wandb_logging=wandb_logging,
    )

    if rank in [0, torch.device("cpu")]:
        # save model and optimizer state dicts
        save_checkpoint(
            state=checkpoint,
            filename=os.path.join(
                args.saving_path,
                f"lstm_cp_{dt.now().strftime('%dp%mp%Y_%Hp%M')}.pt",
            ),
        )

    # destroy process group if DDP was used (for clean exit)
    if args.use_ddp:
        cleanup()

    if rank in [0, torch.device("cpu")]:
        if wandb_logging:
            wandb.finish()

        # load checkpoint with lowest validation loss for final evaluation;
        # device does not need to be specified, since the checkpoint will be
        # loaded on the CPU or GPU with ID 0 depending on where the checkpoint
        # was saved
        load_checkpoint(model=model, checkpoint=checkpoint)

        # check accuracy on train and test set and produce confusion matrix
        check_accuracy(train_loader, model, mode="train", device=rank)
        check_accuracy(test_loader, model, mode="test", device=rank)


if __name__ == "__main__":
    parser = get_parser()
    args = retrieve_args(parser)

    # Setup basic configuration for logging
    logging.basicConfig(
        filename=os.path.join(args.saving_path, "run.log"),
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s",
    )
    if args.config is not None and os.path.exists(args.config):
        logging.info(f"Config file '{args.config}' found and loaded.")
    logging.info(args)

    # define world size (number of GPUs)
    world_size = torch.cuda.device_count()

    if torch.cuda.is_available():
        list_gpus = [torch.cuda.get_device_name(i) for i in range(world_size)]
        logging.info(f"\nGPU(s): {list_gpus}\n")

    if args.use_ddp and world_size > 1:
        # When using a single GPU per process and per
        # DistributedDataParallel, we need to divide the batch size
        # ourselves based on the total number of GPUs of the current node.
        args.batch_size = int(args.batch_size / world_size)
        mp.spawn(main, args=(world_size, args), nprocs=world_size)
    else:
        args.use_ddp = False
        main(
            rank=0 if world_size >= 1 else torch.device("cpu"),
            world_size=1,
            args=args,
        )
