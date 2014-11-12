type file;

app (external ex) combine1 (string lat, string var, string inputDir, string outputDir, string param) {
   combine1 lat var inputDir outputDir param;
}

app (file output) findParts (string workDir) {
   findParts workDir stdout=@output;
}

string params = strcat(arg("workdir"), "/params.psims");
string variables[] = strsplit(strcat(arg("variables"), ",", arg("cal_vars")), ",");
string lats[] = readData(findParts(arg("workdir"))); 
string partDir = strcat(arg("workdir"), "/parts");
string varDir = strcat(arg("workdir"), "/var_files");

# parts -> var_files
tracef("\nRunning combine1 . . . %k\n", lats);
foreach lat in lats {
   foreach var in variables {
      external e;
      e = combine1(lat, var, partDir, varDir, params);
   }
}
