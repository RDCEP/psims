type file;

app (external e) combinelat (string params, string cwd, string split) {
    combinelat "--params" params "--inputdir" cwd "--outputdir" cwd "--split" split;
}

string cwd    = arg("cwd");
string param  = arg("param");
string split  = arg("split");

tracef("\nRunning combine lats . . .\n");
external e;
e = combinelat(param, cwd, split);
