type file;

app (external e) aggregate (string rundir, string param, string var, int chunk) {
    aggregate "-i" rundir "-p" param "-v" var "-c" chunk;
}

string cwd    = arg("cwd");
string param  = arg("param");
string vars[] = strsplit(strcat(arg("variables"), ",", arg("cal_vars")), ",");
int numchunks = toInt(arg("num_chunks"));

tracef("\nRunning aggregate . . .\n");
foreach var in vars {
    foreach chunk in [1 : numchunks] {
        external e;
        e = aggregate(cwd, param, var, chunk);
    }
}
