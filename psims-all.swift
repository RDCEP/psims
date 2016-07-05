type file;

app (external e) pysims (string campaign, string param, string tlatidx, string tlonidx, int slatidx, int slonidx, int split, string rundir) {
	pysims "--campaign" campaign "--param" param "--tlatidx" tlatidx "--tlonidx" tlonidx "--slatidx" slatidx "--slonidx" slonidx "--split" split "--rundir" rundir;
}

app (file output) findLats (string workDir, external[string][][] exts) {
    findLats workDir stdout=@output;
}

app (external e) combinelon (string params, string inputdir, string cwd, int split, external[string][][] exts) {
    combinelon "--params" params "--inputdir" inputdir "--outputdir" cwd "--split" split;
}

app (external e) combinelat (string params, string cwd, int split, external[string] exts) {
    combinelat "--params" params "--inputdir" cwd "--outputdir" cwd "--split" split;
}

app (external e) aggregate (string rundir, string param, string var, int chunk, external ext) {
    aggregate "-i" rundir "-p" param "-v" var "-c" chunk;
}

string campaign   = arg("campaign");
string param      = arg("param");
string rundir     = arg("cwd");
int split         = toInt(arg("split"));
string tileList[] = readData("tileList.txt");
string vars[]     = strsplit(strcat(arg("variables"), ",", arg("cal_vars")), ",");
int numchunks     = toInt(arg("num_chunks"));

external parts_e[string][][];
external combinelon_e[string];
external combinelat_e;
external aggregate_e[string][int];

# Parts
tracef("\nCreating part files . . .\n");
foreach tile in tileList {
    string indices[] = strsplit(tile, "/");
    string tlatidx = indices[0];
    string tlonidx = indices[1];
    foreach slatidx in [1:split] {
        foreach slonidx in [1:split] {
	    external e;
            e = pysims(campaign, param, tlatidx, tlonidx, slatidx, slonidx, split, rundir);
	    parts_e[tile][slatidx][slonidx] = e;
	}
   }
}

# Combinelon
tracef("\nRunning combine lons . . .%k\n", parts_e);
file find_lats_txt <"findLats.txt">;
find_lats_txt = findLats(rundir, parts_e);
string lats[] = readData(find_lats_txt);
foreach lat in lats {
    external e;
    e = combinelon(param, lat, rundir, split, parts_e);
    combinelon_e[lat] = e;
}

# Combinelat
tracef("\nRunning combine lats . . .%k\n", combinelon_e);
combinelat_e = combinelat(param, rundir, split, combinelon_e);

# Aggregate
tracef("\nRunning aggregate . . .%k\n", combinelat_e);
foreach var in vars {
    foreach chunk in [1 : numchunks] {
        external e;
        e = aggregate(rundir, param, var, chunk, combinelat_e);
	aggregate_e[var][chunk] = e;
    }
}
