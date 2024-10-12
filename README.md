# Rithmic Account PnL and Position Information

This is a standalone application gets the following account information:

* The account balance.
* The account margin balance.
* The account daily profit loss.
* The number of open/closed positions for assets traded for the day.
* The number of long/short orders filled for assets traded for the day.
* The open profit/loss for each asset with an open position.
* The closed profit/loss for each asset with closed positions.
* The daily profit/loss for each asset traded for the day.


## Prequisites

* You must have either a Rithmic Paper Trading or Rithmic Live account.
* You must pass Rithmic's conformance testing.
* After passing conformance testing, Rithmic will send you a four-character prefix and its system URI.

#### A four-character prefix

After Rithmic sends you the four-character prefix, apply it.

* In `account_pnl_pos_snap_standalone.py`, find the following variable, on `Line 306`:
    * `rq.app_name`
    * Update its value by replacing `CHANGE_ME` with the prefix issued by Rithmic.
    
#### Proto Files

In the library imports section of the `account_pnl_pos_snap_standalone.py` file, you will see references to `_pb2` files.  You must get those from Rithmic and drop them in the `protobuf` directory. These files are found in the API files that you downloaded from Rithmic.

#### SSL Cert File

The application files reference the `rithmic_ssl_cert_auth_params` file.  You should have received that file from Rithmic.  Drop your copy in the root directory.

#### URI

After you pass conformance testing, Rithmic will send you the URI to access its system.  In the `account_pnl_pos_snap_standalone.py` file, go to `Line 434` `(uri = 'CHANGE_ME')` and assign the URI provided by Rithmic to the variable `uri`.
    

## Installation

Download the repo to your hard drive.


## Start App

After downloading the repo, `cd` to `python_rithmic_account_info`.

Run the following command:


python account_pnl_pos_snap_standalone.py [USERNAME] [PASSWORD] [FCM] [IB] [ACCOUNT_ID]


For example, if your Rithmic credentials are **00000000-DEMO/password123** and you want to get account information for account **999999-DEMO** through your **IB (e.g., Ironbeam) and FCM (e.g., Ironbeam)**, then you would run the following command:

```
python account_pnl_pos_snap_standalone.py 00000000-DEMO password123 Ironbeam Ironbeam 999999
``` 

After running the app, you will the account information. The following is an example:

```
NQZ4 number of open positons: 1
NQZ4 number of closed positons: 8
NQZ4 number of long orders filled: 4
NQZ4 number of short orders filled: 5
NQZ4 open pnl: 700.0
NQZ4 closed pnl: 300.0
NQZ4 daily pnl: 1000.0

Account: 999999-DEMO
Account Balance: 60000.0
Margin Balance: 58000.0
Account Daily PnL: 1000.0
```


## In Live Environment

If you wish to trade live, do the following:

* In `account_pnl_pos_snap_standalone.py`, find the variable `system_name`.
* Change its value from `Rithmic Paper Trading` to `Rithmic 01`.
