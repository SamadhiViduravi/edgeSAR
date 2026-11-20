# Audit 1: file identity, report alignment, extraction provenance


## A. Fingerprints

- **PASS** pilot data/cases.jsonl matches the 28 Oct freeze
- **PASS** pilot common.py matches the 28 Oct freeze
- **PASS** pilot baselines.py matches the 28 Oct freeze
- **PASS** pilot analyze.py matches the 28 Oct freeze
- **PASS** pilot run_model.py matches the 28 Oct freeze
- **PASS** allocator packages/allocation/cbba.py matches the hash pinned in harm_config.json
- **PASS** allocator packages/allocation/bids.py matches the hash pinned in harm_config.json
- **PASS** allocator packages/allocation/mission.py matches the hash pinned in harm_config.json
- **PASS** allocator packages/allocation/world.py matches the hash pinned in harm_config.json
- **PASS** allocator packages/allocation/funnel.py matches the hash pinned in harm_config.json
- **PASS** HARM_TEST_PLAN.md matches its frozen hash
- **PASS** results_controls/predictions_end.csv (controls run 1) matches the hash pinned for the harm test
- **PASS** controls run_02 predictions match the hash in its provenance.json; run_02 says: REPRODUCES RUN 1 (21000 rows compared, 0 different)

## B. Report identity

- **PASS** features/case_ids.json lists the 1400 report ids in exactly the order of cases.jsonl
- **PASS** f16 end meta: cases fingerprint, n=1400, dim=2048, prompt P1, server args --embeddings --pooling last -b 1024 -ub 1024, model file Llama-3.2-1B-Instruct-f16.gguf, one row per response, build b11901-5320c87ff, max prompt 667 tokens
- **PASS** f16 prefix meta: cases fingerprint, n=1400, dim=2048, prompt P1, server args --embeddings --pooling last -b 1024 -ub 1024, model file Llama-3.2-1B-Instruct-f16.gguf, one row per response, build b11901-5320c87ff, max prompt 670 tokens
- **PASS** Q8_0 end meta: cases fingerprint, n=1400, dim=2048, prompt P1, server args --embeddings --pooling last -b 1024 -ub 1024, model file Llama-3.2-1B-Instruct-Q8_0.gguf, one row per response, build b11901-5320c87ff, max prompt 667 tokens
- **PASS** Q8_0 prefix meta: cases fingerprint, n=1400, dim=2048, prompt P1, server args --embeddings --pooling last -b 1024 -ub 1024, model file Llama-3.2-1B-Instruct-Q8_0.gguf, one row per response, build b11901-5320c87ff, max prompt 670 tokens
- **PASS** Q4_K_M end meta: cases fingerprint, n=1400, dim=2048, prompt P1, server args --embeddings --pooling last -b 1024 -ub 1024, model file Llama-3.2-1B-Instruct-Q4_K_M.gguf, one row per response, build b11901-5320c87ff, max prompt 667 tokens
- **PASS** Q4_K_M prefix meta: cases fingerprint, n=1400, dim=2048, prompt P1, server args --embeddings --pooling last -b 1024 -ub 1024, model file Llama-3.2-1B-Instruct-Q4_K_M.gguf, one row per response, build b11901-5320c87ff, max prompt 670 tokens

## C/D. Extraction logs: settings and order

- **PASS** f16 log command: `D:\llama\llama-server.exe -m D:\llama\models\Llama-3.2-1B-Instruct-f16.gguf --host 127.0.0.1 --port 8091 -ngl 99 -c 4096 -np 1 -t 6 --embeddings --pooling last -b 1024 -ub 1024`
- **PASS** f16 log has 2800 embedding requests (expected 2 x 1400)
- **PASS** f16: no request truncated; longest prompt 670 tokens < batch 1024
- **PASS** Q8_0 log command: `D:\llama\llama-server.exe -m D:\llama\models\Llama-3.2-1B-Instruct-Q8_0.gguf --host 127.0.0.1 --port 8091 -ngl 99 -c 4096 -np 1 -t 6 --embeddings --pooling last -b 1024 -ub 1024`
- **PASS** Q8_0 log has 2800 embedding requests (expected 2 x 1400)
- **PASS** Q8_0: no request truncated; longest prompt 670 tokens < batch 1024
- **PASS** Q4_K_M log command: `D:\llama\llama-server.exe -m D:\llama\models\Llama-3.2-1B-Instruct-Q4_K_M.gguf --host 127.0.0.1 --port 8091 -ngl 99 -c 4096 -np 1 -t 6 --embeddings --pooling last -b 1024 -ub 1024`
- **PASS** Q4_K_M log has 2800 embedding requests (expected 2 x 1400)
- **PASS** Q4_K_M: no request truncated; longest prompt 670 tokens < batch 1024
- **PASS** the three models received the identical sequence of 2800 prompt lengths (same prompts, same order)
- **PASS** second half = 'prefix' prompts: prefix minus end token count is [3] for every report
- **PASS** log token counts follow the prompt length of the reports in case order: Pearson 0.9645, Spearman 0.9616 (200 random orders: max |r| 0.068)
- **PASS** meta prompt_tokens_max 667 = longest 'end' prompt in the log 667

## E. Vectors

- **PASS** f16 end vectors: shape (1400, 2048), all finite, L2 norm 1.0000000 to 1.0000000 (unit length: the server normalises)
- **PASS** Q8_0 end vectors: shape (1400, 2048), all finite, L2 norm 1.0000000 to 1.0000000 (unit length: the server normalises)
- **PASS** Q4_K_M end vectors: shape (1400, 2048), all finite, L2 norm 1.0000000 to 1.0000000 (unit length: the server normalises)
- **INFO** Q8_0 vs FP16, same-report cosine mean 0.9987 (min 0.9978, max 0.9992)
- **INFO** Q8_0 nearest-neighbour recovery [raw, all 1400]: 95.9% (median rank of true partner 0, worst 4)
- **INFO** Q8_0 nearest-neighbour recovery [DIAGNOSTIC centring (own 1400-report mean of each set; uses B), all 1400]: 100.0% (median rank of true partner 0, worst 0)
- **INFO** Q8_0 nearest-neighbour recovery [correction as used (Q - delta_devA), held B 400]: 100.0% (median rank of true partner 0, worst 0)
- **INFO** Q8_0 nearest-neighbour recovery [raw, held B 400]: 97.8% (median rank of true partner 0, worst 1)
- **INFO** Q4_K_M vs FP16, same-report cosine mean 0.9598 (min 0.9465, max 0.9684)
- **INFO** Q4_K_M nearest-neighbour recovery [raw, all 1400]: 4.1% (median rank of true partner 104.5, worst 1342)
- **INFO** Q4_K_M nearest-neighbour recovery [DIAGNOSTIC centring (own 1400-report mean of each set; uses B), all 1400]: 83.0% (median rank of true partner 0, worst 248)
- **INFO** Q4_K_M nearest-neighbour recovery [correction as used (Q - delta_devA), held B 400]: 88.5% (median rank of true partner 0, worst 12)
- **INFO** Q4_K_M nearest-neighbour recovery [raw, held B 400]: 11.0% (median rank of true partner 43, worst 369)

## F. Does gen_cases.py reproduce the frozen cases.jsonl?

- **PASS** gen_cases.py (seed 20261026, defaults) regenerates cases.jsonl byte for byte after line endings are normalised (the frozen file has Windows CRLF line endings; its frozen hash is of the CRLF file)

## Reading

- **INFO** Alignment is established by report ids (case_ids.json), the cases fingerprint in every meta file, and the request order in the server logs. Nearest-neighbour recovery is a supporting diagnostic only: it cannot prove the absence of an extraction bug.
