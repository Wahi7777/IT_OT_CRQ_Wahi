# Lambda runtime benchmark

## Conclusion

`LAMBDA_SUITABLE_WITH_CONSTRAINTS`

All four representative 500,000-simulation runs completed locally in less than ten seconds of process wall time. IT peak RSS was approximately 527 MiB; OT peak RSS was approximately 1.14–1.15 GiB. The workload was effectively single-core. Temporary files remained below 2 MiB in the measured temporary directory, while input/output workbooks were about 0.63–0.66 MiB each.

| Case | Router run | Engine refresh including engine workbook I/O | Excel router/report overhead | Peak RSS | Result JSON | Validation |
|---|---:|---:|---:|---:|---:|---|
| IT Financial Services | 8.355 s | 1.948 s | 6.407 s | 527 MiB | 71 KiB | PASS |
| OT Power Generation | 6.883 s | 2.459 s | 4.423 s | 1,165 MiB | 673 KiB | PASS |
| OT Energy Assets | 6.905 s | 2.447 s | 4.458 s | 1,165 MiB | 672 KiB | PASS |
| OT Manufacturing | 6.849 s | 2.444 s | 4.406 s | 1,180 MiB | 672 KiB | PASS |

Assessment workbook preparation/save took about 1.14–1.16 seconds. Cold Python imports measured inside the process took 0.06–0.11 seconds. CPU use was approximately one full core.

The V1 Lambda configuration should therefore begin benchmarking at no less than 2,048 MB and should test 3,008 MB or higher because Lambda allocates CPU in proportion to memory. Set a conservative timeout such as 120 seconds for V1 while retaining the platform's normal request/job timeout policy. The measured disk footprint fits the default 512 MB `/tmp`, but package extraction, S3 transfer and concurrency must be tested in the actual Lambda artifact.

AWS currently permits up to 15 minutes, 10,240 MB memory, and configurable 512–10,240 MB ephemeral storage. These service limits exceed the local measurements, but they do not guarantee equivalent performance. Sources: https://docs.aws.amazon.com/lambda/latest/dg/gettingstarted-limits.html and https://docs.aws.amazon.com/lambda/latest/dg/configuration-ephemeral-storage.html.

Conditions before confirming production suitability:

1. benchmark the exact Lambda deployment package and architecture;
2. measure cold start, VPC/RDS initialization and S3 transfer;
3. run concurrent invocations and enforce per-tenant/run concurrency limits;
4. confirm `/tmp` cleanup and no state reuse between assessments;
5. use runtime-neutral calculation entry points so Fargate remains a packaging change, not an engine change.

Machine-readable evidence is in `docs/productisation/benchmark-results.json`. The benchmark command creates only temporary workbooks and never writes accepted outputs.
