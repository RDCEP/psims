type file;

app (file tar_out, file part_out) RunpSIMS (string latidx, string lonidx, string input_files)
{
   RunpSIMS latidx lonidx @tar_out input_files;
}

string gridLists[] = readData("gridList.txt");
file scenario_input[] <filesys_mapper; location=@arg("campaign"), pattern="*">;
file common_input[] <filesys_mapper; location=@arg("refdata"), pattern="*">;	
file params <single_file_mapper; file=@strcat(@arg("workdir"), "/params.psims")>;
tracef("\nCreating part files...\n");

foreach g,i in gridLists {

   // Input files
   file weather_input[] <filesys_mapper; location=@strcat(@arg("weather"), "/", gridLists[i]), pattern="*">; 
   file soils_input[] <filesys_mapper; location=@strcat(@arg("soils"), "/", gridLists[i]), pattern="*">; 

   // Output files
   file tar_output <single_file_mapper; file=@strcat("output/", gridLists[i], "output.tar.gz")>;
   file part_output <single_file_mapper; file=@strcat("parts/", gridLists[i], ".psims.nc")>;

   // RunpSIMS
   string gridNames[] = @strsplit(g, "/");
   string files_in = @strcat(@scenario_input, " ", @weather_input, " ", @soils_input, " ", @common_input, " ", @params);
   (tar_output, part_output) = RunpSIMS(gridNames[0], gridNames[1], files_in);

}
