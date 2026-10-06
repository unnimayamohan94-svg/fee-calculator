
from flask import Flask,render_template,jsonify,request
import sqlite3
from pathlib import Path

app=Flask(__name__)
DB=Path(__file__).with_name("transfer_fee.db")
CURRENCIES={"USD":"00001","YER":"00003","SAR":"00004"}

def db():
    c=sqlite3.connect(DB);c.row_factory=sqlite3.Row;return c

def component(r,amt):
    raw=amt*float(r["PCNT"])/100.0
    lo=float(r["MIN_FEE"]);hi=float(r["MAX_FEE"])
    fee=max(lo,min(hi,raw))
    cap="Min fee" if raw<lo else ("Max fee" if raw>hi else "None")
    return raw,fee,cap

@app.get("/")
def index(): return render_template("index.html")

@app.get("/api/channel/<channel>/products")
def products(channel):
    with db() as c:
        return jsonify([dict(r) for r in c.execute("SELECT PROD_ID,PROD_NAME FROM product WHERE CHANNEL=? ORDER BY PROD_ID",(channel,))])

@app.get("/api/channel/<channel>/transactions/<int:pid>")
def transactions(channel,pid):
    with db() as c:
        rows=c.execute("""SELECT t.TRAN_ID,t.TRAN_NAME FROM prod_detl pd JOIN tran t
        ON t.CHANNEL=pd.CHANNEL AND t.TRAN_ID=pd.TRAN_ID
        WHERE pd.CHANNEL=? AND pd.PROD_ID=? ORDER BY t.TRAN_ID""",(channel,pid))
        return jsonify([dict(r) for r in rows])

@app.get("/api/channel/<channel>/zones")
def zones(channel):
    with db() as c:
        return jsonify([dict(r) for r in c.execute("SELECT ZONE_ID,ZONE_CODE,ZONE_NAME FROM zone WHERE CHANNEL=? ORDER BY ZONE_ID",(channel,))])

@app.get("/api/channel/<channel>/mappings")
def mappings(channel):
    with db() as c:
        rows=c.execute("""SELECT p.PROD_ID,p.PROD_NAME,t.TRAN_ID,t.TRAN_NAME,pd.FEE_GROUP_ID,pd.EXTRA_CMSN_ID
        FROM prod_detl pd
        JOIN product p ON p.CHANNEL=pd.CHANNEL AND p.PROD_ID=pd.PROD_ID
        JOIN tran t ON t.CHANNEL=pd.CHANNEL AND t.TRAN_ID=pd.TRAN_ID
        WHERE pd.CHANNEL=? ORDER BY p.PROD_ID,t.TRAN_ID""",(channel,)).fetchall()
        out=[]
        for r in rows:
            d=dict(r);d["FEES"]={}
            for cur,code in CURRENCIES.items():
                fs=c.execute("""SELECT DISTINCT f.FEE_ID FROM group_fees_detl g
                JOIN fee f ON f.CHANNEL=g.CHANNEL AND f.FEE_ID=g.FEES_ID
                WHERE g.CHANNEL=? AND g.FEES_GROUP_ID=? AND f.CRCY_TYPE_CODE=?""",
                (channel,r["FEE_GROUP_ID"],code)).fetchall()
                d["FEES"][cur]=[x["FEE_ID"] for x in fs]
            out.append(d)
        return jsonify(out)

@app.post("/api/calculate")
def calculate():
    x=request.get_json(force=True)
    try:
        channel=x["channel"]; pid=int(x["productId"]); tid=int(x["transactionId"]); cur=x["currency"]; amt=float(x["amount"])
    except Exception:
        return jsonify(error="Invalid input."),400
    if channel not in ("MFLOOS","KJ") or cur not in CURRENCIES or amt<=0:
        return jsonify(error="Invalid channel, currency or amount."),400

    with db() as c:
        pds=c.execute("SELECT * FROM prod_detl WHERE CHANNEL=? AND PROD_ID=? AND TRAN_ID=?",(channel,pid,tid)).fetchall()
        if len(pds)!=1:return jsonify(error="No unique active Product + Transaction mapping is available."),404
        pd=pds[0]

        fees=c.execute("""SELECT DISTINCT f.* FROM group_fees_detl g
        JOIN fee f ON f.CHANNEL=g.CHANNEL AND f.FEE_ID=g.FEES_ID
        WHERE g.CHANNEL=? AND g.FEES_GROUP_ID=? AND f.CRCY_TYPE_CODE=?""",
        (channel,pd["FEE_GROUP_ID"],CURRENCIES[cur])).fetchall()
        if len(fees)==0:return jsonify(error=f"No {cur} fee configuration available for the selected Product + Transaction."),404
        if len(fees)>1:return jsonify(error=f"Multiple active {cur} fee configurations were found."),409
        fee=fees[0]

        pn=c.execute("SELECT PROD_NAME FROM product WHERE CHANNEL=? AND PROD_ID=?",(channel,pid)).fetchone()["PROD_NAME"]
        tn=c.execute("SELECT TRAN_NAME FROM tran WHERE CHANNEL=? AND TRAN_ID=?",(channel,tid)).fetchone()["TRAN_NAME"]
        base={"channel":channel,"productName":pn,"transactionName":tn,"currency":cur,"feeGroupId":pd["FEE_GROUP_ID"],"feeId":fee["FEE_ID"]}

        if cur=="YER":
            names={"High":"00001","Medium":"00003","Low":"00002"}
            fc=names.get(x.get("fromLiquidity"));tc=names.get(x.get("toLiquidity"))
            if not fc or not tc:return jsonify(error="Invalid liquidity selection."),400
            mr=c.execute("SELECT CALCULATED_LQDTY FROM liquidity_matrix WHERE FROM_LQDTY=? AND TO_LQDTY=?",(fc,tc)).fetchone()
            calc_code=mr["CALCULATED_LQDTY"]
            calc_name=c.execute("SELECT NAME FROM liquidity_type WHERE CODE=?",(calc_code,)).fetchone()["NAME"]

            hr=c.execute("""SELECT * FROM fee_detl WHERE CHANNEL=? AND FEE_ID=? AND LQDTY='00001'
            AND ? BETWEEN RNGE_STRT AND RNGE_END ORDER BY RNGE_STRT DESC LIMIT 1""",(channel,fee["FEE_ID"],amt)).fetchone()
            cr=c.execute("""SELECT * FROM fee_detl WHERE CHANNEL=? AND FEE_ID=? AND LQDTY=?
            AND ? BETWEEN RNGE_STRT AND RNGE_END ORDER BY RNGE_STRT DESC LIMIT 1""",(channel,fee["FEE_ID"],calc_code,amt)).fetchone()
            if not hr or not cr:
                msg="Fee configuration missing for the selected Product, Transaction, Currency and Amount." if channel=="KJ" else f"No matching fee-detail configuration is available for {amt:,.2f} YER."
                return jsonify(error=msg),404

            hraw,hfee,hcap=component(hr,amt);craw,cfee,ccap=component(cr,amt)
            base.update(mode="YER",calculatedLiquidity=calc_name,
                high={"raw":hraw,"fee":hfee,"percentage":hr["PCNT"],"rangeStart":hr["RNGE_STRT"],"rangeEnd":hr["RNGE_END"],"minFee":hr["MIN_FEE"],"maxFee":hr["MAX_FEE"],"capApplied":hcap},
                calculated={"raw":craw,"fee":cfee,"percentage":cr["PCNT"],"rangeStart":cr["RNGE_STRT"],"rangeEnd":cr["RNGE_END"],"minFee":cr["MIN_FEE"],"maxFee":cr["MAX_FEE"],"capApplied":ccap},
                finalFee=max(0,cfee-hfee))
            return jsonify(base)

        liq=c.execute("SELECT FOREIGN_FEE_LQDTY FROM channel_config WHERE CHANNEL=?",(channel,)).fetchone()["FOREIGN_FEE_LQDTY"]
        fr=c.execute("""SELECT * FROM fee_detl WHERE CHANNEL=? AND FEE_ID=? AND LQDTY=?
        AND ? BETWEEN RNGE_STRT AND RNGE_END ORDER BY RNGE_STRT DESC LIMIT 1""",(channel,fee["FEE_ID"],liq,amt)).fetchone()
        if not fr:
            msg="Fee configuration missing for the selected Product, Transaction, Currency and Amount." if channel=="KJ" else f"No matching High fee-detail configuration is available for {amt:,.2f} {cur}."
            return jsonify(error=msg),404

        try:sz=int(x["senderZoneId"]);rz=int(x["receiverZoneId"])
        except Exception:return jsonify(error="Select both Sender Zone and Receiver Zone."),400
        sp=c.execute("""SELECT EXTRA_CMSN_PRCNTG FROM extra_commission
        WHERE CHANNEL=? AND EXTRA_CMSN_ID=? AND ZONE_ID=? AND CURRENCY=?""",
        (channel,pd["EXTRA_CMSN_ID"],sz,CURRENCIES[cur])).fetchone()
        rp=c.execute("""SELECT EXTRA_CMSN_PRCNTG FROM extra_commission
        WHERE CHANNEL=? AND EXTRA_CMSN_ID=? AND ZONE_ID=? AND CURRENCY=?""",
        (channel,pd["EXTRA_CMSN_ID"],rz,CURRENCIES[cur])).fetchone()
        if not sp or not rp:return jsonify(error="No Extra Commission configuration available for the selected Product, Transaction, Currency and Zone."),404

        fraw,ffee,fcap=component(fr,amt)
        sv=float(sp["EXTRA_CMSN_PRCNTG"]);rv=float(rp["EXTRA_CMSN_PRCNTG"])
        raw_extra=amt*(sv-rv)/100.0
        extra=raw_extra if raw_extra>0 else 0.0
        base.update(mode="FX",foreignLiquidityCode=liq,
            transactionFee={"raw":fraw,"fee":ffee,"percentage":fr["PCNT"],"rangeStart":fr["RNGE_STRT"],"rangeEnd":fr["RNGE_END"],"minFee":fr["MIN_FEE"],"maxFee":fr["MAX_FEE"],"capApplied":fcap},
            senderPercentage=sv,receiverPercentage=rv,rawExtraCommission=raw_extra,extraCommission=extra,totalFee=ffee+extra)
        return jsonify(base)

if __name__=="__main__": app.run(host="127.0.0.1",port=5000,debug=False)
