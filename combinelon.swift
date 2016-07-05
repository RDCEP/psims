type file;

app (file output) findLats (string workDir) {
    findLats workDir stdout=@output;
}

app (external e) combinelon (string params, string inputdir, string cwd, string split) {
    combinelon "--params" params "--inputdir" inputdir "--outputdir" cwd "--split" split; 
}

string cwd    = arg("cwd");
string param  = arg("param");
string split  = arg("split");
string lats[] = readData(findLats(cwd));

tracef("\nRunning combine lons . . .\n");

foreach lat in lats {
    external e;
    e = combinelon(param, lat, cwd, split);
}
