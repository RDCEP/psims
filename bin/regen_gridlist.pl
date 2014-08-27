#!/usr/bin/perl -w

use strict;

my @parts=`find parts -mindepth 2|sed -e s\@parts/\@\@g -e s\@\.part\@\@g|grep -v parts`;
my @gridList=`cat gridList.txt`;
system("mv gridList.txt gridList.txt.orig");

my %doGridRestart = ();

foreach my $grid(@gridList) {
   chomp($grid);
   $doGridRestart{$grid} = 1;
}

foreach my $part(@parts) {
   chomp($part);
   $doGridRestart{$part} = 0;
}

open(GRIDFILE, ">gridList.txt") || die "Unable to open gridlist\n";
while ( my ($gridVal, $doRestart) = each(%doGridRestart) ) {
   if($doRestart) {
      print GRIDFILE "$gridVal\n";
   }
}
close(GRIDFILE);
