#!/usr/bin/perl -w
use strict;
use Time::Local 'timelocal_nocheck';

# Usage: ./activity-plot.pl run000.log activity-plot.png
if(@ARGV != 2) {
   print "Usage: $0 <log> <image>\n";
   exit 1;
}

# Given "Active: 10", or "HeapMax: 9361686528,", return only values
sub get_value
{
   my $statement = $_[0];
   my $value = (split /:/, $statement)[1];
   $value =~ s/,//g;
   return $value;
}

# Convert Swift time stamp to seconds
sub timestamp_to_seconds
{
   (my $date, my $hhmmss, my @junk) = split('\s+', $_[0]);
   $hhmmss = (split /,/, $hhmmss)[0];
   (my $year, my $month, my $monthday) = split('\-', $date);
   (my $hh, my $mm, my $ss) = split(':', $hhmmss);
   my $time = timelocal_nocheck($ss, $mm, $hh, $monthday-1, $month, $year);
   return $time;
}
my $first_timestamp=0;
my $log_filename=shift;
my $image=shift;

my $data_filename = $image;
$data_filename =~ s{\.[^.]+$}{};
$data_filename .= ".dat";

my $gp_filename = $image;
$gp_filename =~ s{\.[^.]+$}{};
$gp_filename .= ".gp";

open(LOG, "$log_filename") || die "Unable to open $log_filename\n";
open(DAT, ">$data_filename") || die "Unable to create $data_filename\n";

while(<LOG>) {
   my $line = $_;
   if( $line =~ m/RuntimeStats\$ProgressTicker/ ) {
      if( $line !~ m/HeapMax/ ) { 
         my @words = split('\s+', $line);
         my $timestamp = timestamp_to_seconds($line);
         if($first_timestamp == 0) { $first_timestamp = $timestamp; $timestamp=0; } 
         else { $timestamp = $timestamp - $first_timestamp; }   
         my ($active, $stagein, $stageout, $completed) = (0) x 4;
         foreach my $word(@words) {
            if    ($word =~ /Active:/)        { $active    = get_value($word); }
            elsif ($word =~ /successfully:/)  { $completed = get_value($word); }
            elsif ($word =~ /in:/)            { $stagein   = get_value($word); }
            elsif ($word =~ /out:/)           { $stageout  = get_value($word); }
         }
         print DAT "$timestamp $stagein $active $stageout $completed\n";
      }
   }
}

close(DAT);
open(GP, ">$gp_filename") || die "Unable to create $gp_filename";

my $gp = <<END;
set term png enhanced size 1000,1000
set output "$image"
set xlabel "Time in seconds"

set multiplot layout 4,1
plot '$data_filename' using 1:3:(0) title 'Active' with lines
plot '$data_filename' using 1:2:(0) title 'Staging in' with lines
plot '$data_filename' using 1:4:(0) title 'Staging out' with lines
plot '$data_filename' using 1:5:(0) title 'Completed' with lines
END

print GP $gp; 
close(GP);
system("gnuplot $gp_filename");
unlink("$gp_filename");

