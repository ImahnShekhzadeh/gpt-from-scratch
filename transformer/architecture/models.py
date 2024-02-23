import math
from typing import Dict, List, Optional

import torch
from encoding import PositionalEncoding
from torch import Tensor, nn

from layers import DecoderBlock, EncoderBlock


def expand_mask(mask: torch.Tensor) -> torch.Tensor:
    """
    Helper function to support different mask shapes.
    Output shape supports `(batch_size, num_heads, seq_length, seq_length)`
    If 2D: broadcasted over `batch_size` and `num_heads`
    If 3D: broadcasted over `num_heads`
    If 4D: leave as is

    Args:
        mask: Mask.
    """
    assert (
        mask.ndim >= 2
    ), "Mask must be at least 2-dimensional with `seq_length x seq_length`"
    if mask.ndim == 3:
        mask = mask.unsqueeze(1)
    while mask.ndim < 4:
        mask = mask.unsqueeze(0)
    return mask


class Encoder(nn.Module):
    def __init__(
        self,
        num_layers: int,
        embed_dim: int,
        num_heads: int,
        dim_feedfwd: int = 2048,
        dropout: bool = 0.0,
        use_bias: bool = False,
    ) -> None:
        """
        Transformer encoder.

        Args:
            num_layers: Number of times to stack the encoder block.
            embed_dim: Embedding dim, referred to as `d_model` in [1]
            num_heads: Number of heads, `h` in [1]
            dim_feedfwd: Hidden dimension when applying two-layer MLP
            dropout: Amount of dropout to be applied.
            use_bias: Whether a bias term is used. Default is `False`

        [1] http://arxiv.org/abs/1706.03762
        """
        self.num_layers = num_layers
        self.encoder_block = EncoderBlock(
            embed_dim=embed_dim,
            num_heads=num_heads,
            dim_feedfwd=dim_feedfwd,
            dropout=dropout,
            use_bias=use_bias,
        )

    def forward(
        self, x: torch.Tensor, mask: Optional[torch.Tensor] = None
    ) -> torch.Tensor:
        """
        Forward pass.

        Args:
            x: Input tensor of shape `(N, seq_length, input_dim)`
            mask: Mask, either 2D, 3D or 4D

        Returns:
            Output tensor of shape `(N, seq_length, input_dim)`
        """
        for _ in range(self.num_layers):
            x = self.encoder_block(
                x=x,
                mask=mask,
            )

        return x

    def _get_attn_maps(
        self, mask: Optional[torch.Tensor] = None
    ) -> List[torch.Tensor]:
        """
        Retrieve the learned attention maps per head.

        Args:
            mask: Mask, either 2D, 3D or 4D

        Returns:
            List of PyTorch tensors containing the attention weights per
            encoder block, where each tensor is of shape
            `(N, num_heads, seq_length, seq_length)`
        """
        attn_maps = []

        for _ in range(self.num_layers):
            _, attn_weights = self.encoder_block.multihead_attn(
                x=x,
                mask=mask,
                return_attention=True,
            )
            x = self.encoder_block(
                x=x,
                mask=mask,
            )
            attn_maps.append(attn_weights)

        return attn_maps


class Decoder(nn.Module):
    def __init__(
        self,
        num_layers: int,
        embed_dim: int,
        num_heads: int,
        dim_feedfwd: int,
        dropout: bool = 0.0,
        use_bias: bool = False,
    ) -> None:
        """
        Transformer decoder.

        Args:
            --- cf. `Encoder` ---
        """
        self.num_layers = num_layers
        self.decoder_block = DecoderBlock(
            embed_dim=embed_dim,
            num_heads=num_heads,
            dim_feedfwd=dim_feedfwd,
            dropout=dropout,
            use_bias=use_bias,
        )

    def forward(
        self,
        x: torch.Tensor,
        encoder_output: torch.Tensor,
        mask: torch.Tensor,
    ) -> torch.Tensor:
        """
        Forward pass.

        Args:
            x: Input tensor of shape `(N, seq_length, input_dim)`
                (`input_dim = embed_dim = d_model` in [1])
            mask: Mask, either 2D, 3D or 4D

        Returns:
            Output tensor of shape `(N, seq_length, input_dim)`

        [1] http://arxiv.org/abs/1706.03762
        """
        for _ in range(self.num_layers):
            x = self.decoder_block(
                x=x,
                encoder_output=encoder_output,
                mask=mask,
            )

        return x


class Transformer(nn.Module):
    def __init__(
        self,
        num__encoder_layers: int,
        num__decoder_layers: int,
        embedding_dim: int,
        num_heads: int,
        vocab_size: int,
        seq_length: int = int(1e4),
        dim_feedfwd: int = 2048,
        dropout_rate: float = 0.0,
        use_bias: bool = False,
    ) -> None:
        """
        Transformer model.

        Args:
            num__encoder_layers: Number of times to stack the encoder block.
            num__decoder_layers: Number of times to stack the decoder block.
            embedding_dim: Embedding dim, referred to as `d_model` in [1].
            num_heads: Number of heads for the multi-head attention.
            vocab_size: Vocabulary size of the tokenizer.
            seq_length: Maximum expected sequence length.
            dim_feedfwd: Hidden dimension when applying two-layer MLP.
            dropout_rate: Dropout rate.
            use_bias: Whether a bias term is used when performing the
                self-attention calculation. Default is `False`.

        Returns:
            Output tensor of shape `(N, num_classes)`

        [1] http://arxiv.org/abs/1706.03762
        """
        super().__init__()

        self.embed_dim = embedding_dim
        self.encoder = Encoder(
            num_layers=num__encoder_layers,
            embed_dim=embedding_dim,
            num_heads=num_heads,
            dim_feedfwd=dim_feedfwd,
            dropout=dropout_rate,
            use_bias=use_bias,
        )
        self.decoder = Decoder(
            num_layers=num__decoder_layers,
            embed_dim=embedding_dim,
            num_heads=num_heads,
            dim_feedfwd=dim_feedfwd,
            dropout=dropout_rate,
            use_bias=use_bias,
        )
        self.pos_encod = PositionalEncoding(
            max__seq_length=seq_length,
            embed_dim=embedding_dim,
        )
        self.embedding = nn.Embedding(
            num_embeddings=vocab_size,
            embedding_dim=embedding_dim,
        )
        self.pre_softmax_linear = nn.Linear(
            embedding_dim,
            vocab_size,
            bias=False,
        )
        # weight sharing with the shared embedding
        self.pre_softmax_linear.weight = self.embedding.weight

    def forward(
        self,
        dict_input: Dict[str, Tensor],
    ) -> torch.Tensor:
        """
        Forward pass through the transformer model.

        Args:
            dict_input: Dictionary with the keys "source" and "target",
                each containing a tensor (the tokens) of shape
                `(N, seq_length)`. The "source" tensor is the input to the
                encoder and the "target" tensor is the input to the decoder.

        Returns:
            Output tensor of shape `(N, num_classes)`
        """

        # `(N, seq_length, embed_dim)`
        encoder_input = math.sqrt(self.embed_dim) * self.embedding(
            dict_input["source"]
        )
        encoder_input = self.pos_encod(encoder_input)

        decoder_input = math.sqrt(self.embed_dim) * self.embedding(
            dict_input["target"]
        )
        decoder_input = self.pos_encod(decoder_input)

        # TODO: as described in Sec. 3.4 of [1], the target tokens are shifted
        # by one position to the right
        # TODO: implement decoder mask
        x = self.encoder(encoder_input, mask=None)
        x = self.decoder(decoder_input, mask=None)
        x = self.pre_softmax_linear(x)  # `(N, seq_length, vocab_size)`

        return x