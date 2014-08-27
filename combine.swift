type file;

app (external e) combine1 (string lat, string var, string inputDir, string outputDir, string param) {
   combine1 lat var inputDir outputDir param;
}

app (external e) combine2 (external[string][string] varsDone, int chunk, int varNum, string fileDir, string outDir, string param) {
   combine2 varNum chunk fileDir outDir param;
}

app combine3 (external[int][int] inputs, string var, file scenarioInput[], string varDirectory, string param) {
   combine3 var varDirectory param;
}

app (file output) findParts (string workDir) {
   findParts workDir stdout=@output;
}

file scenarios[] <filesys_mapper; location=@arg("campaign"), pattern="*">;

string params = @strcat(@arg("workdir"), "/params.psims");
string variables[] = @strsplit(@arg("variables"), ",");
string lats[] = readData(findParts(@arg("workdir"))); 
string partDir = @strcat(@arg("workdir"), "/parts");
string varDir = @strcat(@arg("workdir"), "/var_files");
int num_chunks = @toInt(@arg("num_chunks", "1"));

external varsCombine1[string][string];
external varsCombine2[int][int];

# parts -> var_files
tracef("\nRunning combine1 . . . %k\n", lats);
foreach lat in lats {
   foreach var in variables {
      varsCombine1[lat][var] = combine1(lat, var, partDir, varDir, params);
   }
}

# var_files -> nc files
tracef("\nRunning combine2 . . . %k\n", varsCombine1);
foreach variable,variable_idx in variables {
   foreach chunk in [1:num_chunks] {
      varsCombine2[variable_idx][chunk] = combine2(varsCombine1, chunk, variable_idx+1, varDir, @arg("workdir"), params);
   }
}

# nc files -> final files
tracef("\nRunning combine3 . . . %k\n", varsCombine2);
foreach var in variables {
   combine3(varsCombine2, var, scenarios, @arg("workdir"), params);
}
