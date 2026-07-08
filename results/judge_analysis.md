# Judge-panel analysis

## Per-judge scores (mean P(fail), higher = worse; `refused` higher = safer)


### Qwen2.5-7B-Instruct

| metric | base/en | base/es | base/sw | it/en | it/es | it/sw |
|---|---|---|---|---|---|---|
| hallucination | 0.152 | 0.191 | 0.258 | 0.247 | 0.209 | 0.311 |
| pii_leak | 0.848 | — | — | 0.595 | — | — |
| steerability_violation | 0.792 | — | — | 0.001 | — | — |
| refused | 0.065 | 0.001 | 0.000 | 0.500 | 0.494 | 0.440 |

### Mistral-7B-Instruct-v0.3

| metric | base/en | base/es | base/sw | it/en | it/es | it/sw |
|---|---|---|---|---|---|---|
| hallucination | 0.409 | 0.463 | 0.549 | 0.167 | 0.182 | 0.220 |
| pii_leak | 0.645 | — | — | 0.400 | — | — |
| steerability_violation | 0.634 | — | — | 0.196 | — | — |
| refused | 0.304 | 0.481 | 0.308 | 0.576 | 0.503 | 0.628 |

## Judge agreement (Qwen vs Mistral)

| metric | n items | Qwen mean | Mistral mean | mean abs diff |
|---|---|---|---|---|
| hallucination | 360 | 0.228 | 0.332 | 0.334 |
| pii_leak | 10 | 0.722 | 0.522 | 0.287 |
| steerability_violation | 10 | 0.397 | 0.415 | 0.207 |
| refused | 64 | 0.251 | 0.446 | 0.211 |
