type file;

app (external ex) RunpSIMS (string latidx, string lonidx, string tar_out, string part_out, string input_files) {
   RunpSIMS latidx lonidx tar_out part_out input_files;
}

string gridLists[] = readData("gridList.txt");
file scenario_input[] <filesys_mapper; location=arg("campaign"), pattern="*">;
file params <single_file_mapper; file=strcat(arg("workdir"), "/params.psims")>;

tracef("\nCreating part files . . .\n");

foreach g, i in gridLists {
   // Input files
   file soils_input[] <filesys_mapper; location=strcat(arg("soils"), "/", gridLists[i]), pattern="*">; 

   // Output files
   string tar_output = strcat(arg("pwd"), "/output/", gridLists[i], "output.tar.gz");
   string part_output = strcat(arg("pwd"), "/parts/", gridLists[i], ".psims.nc");

   // RunpSIMS
   string gridNames[] = strsplit(g, "/");
   string files_in = strcat(@scenario_input, " ", @soils_input, " ", @params);
   external e;
   e = RunpSIMS(gridNames[0], gridNames[1], tar_output, part_output, files_in);
}
