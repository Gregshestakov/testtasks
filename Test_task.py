from terra_sdk.client.lcd import LCDClient
from terra_sdk.client.lcd.api.wasm import WasmAPI
import pandas as pd
import numpy as np

terra=LCDClient('https://lcd.terra.dev', 'columbus-4')
query = WasmAPI(terra)
ANCHOR_MARKET='terra1sepfj7s0aeg5967uxnfk4thzlerrsktkpelm5s'
ANCHOR_OVERSEER='terra1tmnqgvg567ypvsvk6rwsga3srp7e3lg6u0elp8'
ANCHOR_ORACLE = 'terra1cgg6yef7qcdm070qftghfulaxmllgmvk77nc7t'

print('Start creating loan list')
initial_loan_query = query.contract_query(ANCHOR_MARKET,{"borrower_infos":{}})['borrower_infos']
loans_list=[]
for x in range(len(initial_loan_query)):
    loans_list.append({'wallet_id':initial_loan_query[x]['borrower'],'UST_loan':initial_loan_query[x]['loan_amount']})
support_cycle_loan_query = initial_loan_query

while len(support_cycle_loan_query) == 10 :
    cycle_loan_query=query.contract_query(ANCHOR_MARKET,{"borrower_infos":{"start_after":support_cycle_loan_query[9]['borrower']}})['borrower_infos']
    for x in range(len(cycle_loan_query)):
        loans_list.append({'wallet_id': cycle_loan_query[x]['borrower'],'UST_loan': cycle_loan_query[x]['loan_amount']})
    support_cycle_loan_query=cycle_loan_query

print('Start creating collateral list')
initial_collateral_query=query.contract_query(ANCHOR_OVERSEER,{"all_collaterals": { }})["all_collaterals"]
collaterals_list =[]
for x in range(len(initial_collateral_query)):
    if len(initial_collateral_query[x]['collaterals']) > 1:
        collaterals_list.append({'wallet_id':initial_collateral_query[x]['borrower'],initial_collateral_query[x]['collaterals'][0][0]:initial_collateral_query[x]['collaterals'][0][1],
                                 initial_collateral_query[x]['collaterals'][1][0]:initial_collateral_query[x]['collaterals'][1][1]})
    else:
        collaterals_list.append({'wallet_id':initial_collateral_query[x]['borrower'],initial_collateral_query[x]['collaterals'][0][0]:initial_collateral_query[x]['collaterals'][0][1]})

support_cycle_collateral_query=initial_collateral_query

while len(support_cycle_collateral_query) == 10:
    cycle_collateral_query=query.contract_query(ANCHOR_OVERSEER,{"all_collaterals": {"start_after":support_cycle_collateral_query[9]['borrower']}})["all_collaterals"]
    for x in range(len(cycle_collateral_query)):
        if len(cycle_collateral_query[x]['collaterals']) > 1:
            collaterals_list.append({'wallet_id':cycle_collateral_query[x]['borrower'],cycle_collateral_query[x]['collaterals'][0][0]:cycle_collateral_query[x]['collaterals'][0][1],
                                 cycle_collateral_query[x]['collaterals'][1][0]:cycle_collateral_query[x]['collaterals'][1][1]})
        else:
            collaterals_list.append({'wallet_id':cycle_collateral_query[x]['borrower'],cycle_collateral_query[x]['collaterals'][0][0]:cycle_collateral_query[x]['collaterals'][0][1]})
    support_cycle_collateral_query = cycle_collateral_query

print('Start creating result table')
loan_table=pd.DataFrame(loans_list)
collateral_table = pd.DataFrame(collaterals_list)

bAssets={'wallet_id':'wallet_id','terra1kc87mu460fwkqte29rquh4hc20m54fxwtsx7gp':'bLuna','terra1dzhzukyezv0etz22ud940z7adyv7xgcjkahuun':'bETH'}
collateral_table.rename(columns=bAssets, inplace=True)

result_table = loan_table.merge(collateral_table, on='wallet_id',how='left')

bLuna_price=query.contract_query(ANCHOR_ORACLE,{"price": {"base":'terra1kc87mu460fwkqte29rquh4hc20m54fxwtsx7gp',"quote": "uusd" }})['rate']
bETH_price=query.contract_query(ANCHOR_ORACLE,{"price": {"base":'terra1dzhzukyezv0etz22ud940z7adyv7xgcjkahuun',"quote": "uusd" }})['rate']

result_table['UST_loan']=pd.to_numeric(result_table['UST_loan'],errors="coerce").fillna(0)/1000000
result_table['bLuna']=pd.to_numeric(result_table['bLuna'],errors="coerce").fillna(0)/1000000
result_table['bETH']=pd.to_numeric(result_table['bETH'],errors="coerce").fillna(0)/1000000

result_table['bLuna_denom']=result_table['bLuna']*int(float(bLuna_price))
result_table['bETH_denom']=result_table['bETH']*int(float(bETH_price))
result_table['denom_collateral']=result_table['bLuna_denom']+result_table['bETH_denom']
result_table['ltv'] = (result_table['UST_loan']/result_table['denom_collateral']).fillna(0)
result_table.replace(np.inf, 0, inplace = True)

result_table.to_excel(r".\result_table.xlsx", index=False)
print('Finished succesfully')