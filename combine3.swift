type file;

app (external ex) combine3 (string var, file scenarioInput[], string varDirectory, string param) {
   combine3 var varDirectory param;
}

file scenarios[] <filesys_mapper; location=arg("campaign"), pattern="*">;
string params = strcat(arg("workdir"), "/params.psims");
string variables[] = strsplit(strcat(arg("variables"), ",", arg("cal_vars")), ",");

# nc files -> final files
tracef("\nRunning combine3 . . . \n");
foreach var in variables {
   external e;
   e = combine3(var, scenarios, arg("workdir"), params);
}
