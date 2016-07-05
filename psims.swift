type file;

app (external e) pysims (string campaign, string param, string tlatidx, string tlonidx, int slatidx, int slonidx, int split, string rundir) {
	pysims "--campaign" campaign "--param" param "--tlatidx" tlatidx "--tlonidx" tlonidx "--slatidx" slatidx "--slonidx" slonidx "--split" split "--rundir" rundir;
}

string campaign   = arg("campaign");
string param      = arg("param");
string rundir     = arg("cwd");
int split         = toInt(arg("split"));
string tileList[] = readData("tileList.txt");
external externals[string][][];

tracef("\nCreating part files . . .\n");

foreach tile in tileList {

    string indices[] = strsplit(tile, "/");
    string tlatidx = indices[0];
    string tlonidx = indices[1];

    foreach slatidx in [1:split] {
        foreach slonidx in [1:split] {
	    external e;
            e = pysims(campaign, param, tlatidx, tlonidx, slatidx, slonidx, split, rundir);
	    externals[tile][slatidx][slonidx] = e;
	}
   }
}
