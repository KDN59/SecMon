<?php
// php script for SecMon.html & SecMon.py
// for debug
ini_set('display_errors',1);
error_reporting(E_ALL);

// app use pins states to setup events & prowl msg & chnaged DB
// BCM  7 -> events1 -> pir1
// BCM  6 -> events2 -> ?
// BCM 13 -> events3 -> ?
// BCM 19 -> events4 -> ?
// BCM 26 -> msg
// BCM  0 -> chnaged DB

// $tablePin array of pins for pr_events
$tablePin = array('5', '6', '13', '19', '26');
$tableMod = array(' down', ' up');
$path_DB = '/home/kdn59/Documents/Python/SecMon/SecMonDB.db';

// get the req parameter from URL
$req = $_REQUEST["req"];
//echo $req;
// analise requests from sec.html
if ($req == "reqDB") {
    // connect to DB	
    $db = new SQLite3($path_DB);	
    // read all records from DB
    $res = $db->query('SELECT * FROM events_log');
    while ($row = $res->fetchArray()) {
       echo $row['start']," ",$row['stop']," ",$row['zone']," ",$row['type'],"\n";
    }	
    $db -> close();
}
elseif ($req == "getState") {
    $pr_pir1 = exec('gpio -g read 5');
    $pr_pir2 = exec('gpio -g read 6');
    $pr_pir3 = exec('gpio -g read 13');
    $pr_pir4 = exec('gpio -g read 19');
    $pr_msg  = exec('gpio -g read 26');
    echo $pr_pir1.$pr_pir2.$pr_pir3.$pr_pir4.$pr_msg;
}
elseif (strpos($req, 'setState') !== false) {
    $paramStr = substr($req, 8);    
    for ($i = 0; $i < 5; $i++) {
	exec('gpio -g mode '.$tablePin[$i].$tableMod[(int)$paramStr[$i]]);
    }
}
?>
