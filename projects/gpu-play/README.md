# gpu-play

A PyTorch benchmark that compares CPU vs Apple Silicon GPU (MPS) performance across common deep learning operations, with live terminal progress visualization via [Rich](https://github.com/Textualize/rich).

## What it benchmarks

Each operation is run on both CPU and the Metal Performance Shaders (MPS) backend, with warmup iterations followed by timed iterations. Results are reported as average milliseconds per iteration and an MPS speedup multiplier.

| Benchmark | Description |
|---|---|
| MatMul 2048×2048 | Square matrix multiplication of two 2048×2048 float32 tensors |
| Elementwise 50M | Element-wise addition followed by GELU activation over 50M elements |
| Conv2d 32×64×56×56→128 | Single forward pass of a Conv2d layer (batch=32, 64→128 channels, 56×56 spatial) |
| MLP b64×256 d512 | Transformer-style FFN forward pass (batch=64, seq=256, d_model=512, 4× hidden expansion) |
| Batched MatMul 128×512×512 | Batched matrix multiply across 128 matrices of shape 512×512 |

## Running

```bash
uv run python projects/gpu-play/demo.py
```

Requires an Apple Silicon Mac for MPS acceleration. On other hardware, all benchmarks fall back to CPU-only.

## Tips

- Watch real-time GPU utilisation in **Activity Monitor → Window → GPU History** while the script runs.
- Speedup values are colour-coded in the summary table: green (>1.5×), yellow (>1×), red (<1×).
