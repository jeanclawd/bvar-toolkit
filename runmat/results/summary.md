75 unit tests: 0 pass, 41 fail (an error raised inside the test), 34 error (RunMat could not load or crashed).

| Cause | Tests |
|---|---|
| Stack overflow while lowering (issue 5) | 13 |
| Script or helper called by bare name (issue 8) | 10 |
| Indexing gaps ("Slicing only supported on tensors") | 8 |
| Process crash (core dump) | 7 |
| Type conversion error ("... to f64") | 7 |
| Indexed assignment shape mismatch | 4 |
| Ragged-row matrix literal (issue 1) | 4 |
| Index out of bounds | 4 |
| `if` on a non-scalar logical (MATLAB uses all()) | 3 |
| Compile failure in replication code (issue 4) | 3 |
| Sparse matrix unsupported in kron/mldivide/sum | 2 |
| Dimension mismatch | 2 |
| mtimes on unsupported operand types | 2 |
| Parse failure | 2 |
| Other: fill value must be a scalar  | 1 |
| Other: unable to parse numeric value 'GDP' on line 1 column 2  | 1 |
| Other: semantic function bvar.sv.sv0_params expected 2 inputs, got  | 1 |
| Other: unable to parse date/time text 'now'  | 1 |
