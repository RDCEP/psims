type file;

app (external ex) combine2 (int chunk, int varNum, string fileDir, string outDir, string param) {
   combine2 varNum chunk fileDir outDir param;
}

string params = strcat(arg("workdir"), "/params.psims");
string variables[] = strsplit(strcat(arg("variables"), ",", arg("cal_vars")), ",");
string varDir = strcat(arg("workdir"), "/var_files");
int num_chunks = toInt(arg("num_chunks", "1"));

# var_files -> nc files
tracef("\nRunning combine2 . . .\n");
foreach variable,variable_idx in variables {
   foreach chunk in [1:num_chunks] {
      external e;
      e = combine2(chunk, variable_idx+1, varDir, arg("workdir"), params);
   }
}
