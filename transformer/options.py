import argparse


def get_parser__data_prep() -> argparse.ArgumentParser:
    """
    Get parser for command line arguments when running data preparation script.

    Returns:
        parser for command line arguments
    """
    parser = argparse.ArgumentParser(
        description="Parameters when running data preparation script."
    )
    parser.add_argument(
        "--train_split",
        type=float,
        default=0.8,
        help="Portion of the data to be used for training.",
    )
    parser.add_argument(
        "--dataset",
        type=str,
        default="shakespeare",
        help="Dataset to use. Should be 'shakespeare' or 'openweb'.",
    )
    parser.add_argument(
        "--num_proc",
        type=int,
        default=None,
        help=(
            "Number of processes when downloading and generating the "
            "openweb dataset locally. Multiprocessing is disabled by default."
        ),
    )
    return parser


def get_parser() -> argparse.ArgumentParser:
    """
    Get parser for command line arguments.

    Returns:
        parser for command line arguments
    """
    parser = argparse.ArgumentParser(
        description="Hyperparameters and parameters"
    )

    # generic arguments
    parser.add_argument(
        "--beta_1",
        type=float,
        default=0.9,
        help="beta_1 of the ADAM(W) optimizer.",
    )
    parser.add_argument(
        "--beta_2",
        type=float,
        default=0.999,
        help="beta_2 of the ADAM(W) optimizer.",
    )
    parser.add_argument(
        "--compile_mode",
        type=str,
        default=None,
        help="Mode for compilation of the model when using `torch.compile`.",
    )
    parser.add_argument(
        "--config",
        type=str,
        default=None,
        help="Configuration file.",
    )
    parser.add_argument(
        "--dataset",
        type=str,
        default="shakespeare",
        help="Dataset to use. Should be 'shakespeare' or 'openweb'.",
    )
    parser.add_argument(
        "--eps",
        type=float,
        default=1e-8,
        help="epsilon of the ADAM(W) optimizer.",
    )
    parser.add_argument(
        "--log_freq_loss",
        type=int,
        default=1,
        help="Frequency at which train and val losser are logged.",
    )
    parser.add_argument(
        "--lr_multiplier",
        type=float,
        default=1,
        help=(
            "By which factor to multiply the learning rates of the scheduler "
            "used in the 'Attention is All You Need Paper'."
        ),
    )
    parser.add_argument(
        "--max_norm",
        type=float,
        default=None,
        help="Max norm for gradient clipping.",
    )
    parser.add_argument(
        "--num_workers",
        type=int,
        default=0,
        help="Number of subprocesses used in the dataloaders.",
    )
    parser.add_argument(
        "--pin_memory",
        action="store_true",
        help="Whether tensors are copied into CUDA pinned memory.",
    )
    parser.add_argument(
        "--saving_path",
        type=str,
        default="",
        help="Saving path of files (checkpoints, logs, etc.).",
    )
    parser.add_argument(
        "--seed_number",
        type=int,
        default=None,
        help="If specified, seed number is used for RNG.",
    )
    parser.add_argument(
        "--train",
        action="store_true",
        help=(
            "Whether to train the model for `num_steps` steps, or whether "
            "to do evaluation only."
        ),
    )
    parser.add_argument(
        "--warmup_steps",
        type=int,
        default=4000,
        help="Number of warmup steps for which the LR increases.",
    )
    parser.add_argument(
        "--num_steps",
        type=int,
        default=10,
        help="Number of steps used for training of the NN.",
    )
    parser.add_argument(
        "--batch_size",
        type=int,
        default=1024,
        help="Number of batches that are used for one ADAM update rule.",
    )
    parser.add_argument(
        "--loading_path",
        type=str,
        default=None,
        help=(
            "Path to a checkpoint to be loaded, which is then trained for "
            "`args.num_steps` steps.",
        ),
    )
    parser.add_argument(
        "--use_amp",
        action="store_true",
        help="Whether to use automatic mixed precision (AMP).",
    )
    parser.add_argument(
        "--use_ddp",
        action="store_true",
        help="Whether to use distributed data parallel (DDP).",
    )
    parser.add_argument(
        "--wandb__api_key",
        type=str,
        default=None,
        help="API key for wandb (https://wandb.ai).",
    )

    # transformer-specific arguments
    parser.add_argument(
        "--dim_feedfwd",
        type=int,
        default=2048,
        help="Hidden dimension when applying two-layer MLP in decoder blocks.",
    )
    parser.add_argument(
        "--dropout_rate",
        type=float,
        default=0.0,
        help="Dropout rate for the dropout layer.",
    )
    parser.add_argument(
        "--embedding_dim",
        type=int,
        default=512,
        help="Embedding dimensionality (`d_model`).",
    )
    parser.add_argument(
        "--num__decoder_layers",
        type=int,
        default=6,
        help="Number of times to stack the decoder block.",
    )
    parser.add_argument(
        "--num_heads",
        type=int,
        default=8,
        help="Number of heads for the multi-head attention.",
    )
    parser.add_argument(
        "--block_size",
        type=int,
        default=512,
        help="Maximum context length for predictions",
    )
    parser.add_argument(
        "--max_new_tokens",
        type=int,
        default=100,
        help="Maximum number of tokens to generate.",
    )
    parser.add_argument(
        "--temperature",
        type=float,
        default=1.0,
        help="Temperature for sampling.",
    )
    parser.add_argument(
        "--top_k",
        type=int,
        default=None,
        help="Top-k sampling.",
    )
    parser.add_argument(
        "--vocab_size",
        type=int,
        default=int(3.7e4),
        help="Vocabulary size for the tokenizer.",
    )

    return parser
