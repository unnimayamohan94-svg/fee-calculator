
const $=id=>document.getElementById(id);
const money=n=>new Intl.NumberFormat('en-US',{minimumFractionDigits:2,maximumFractionDigits:2}).format(Number(n));
let channel='MFLOOS';

async function setChannel(next){
 channel=next;document.body.classList.toggle('kj',channel==='KJ');mfBtn.classList.toggle('active',channel==='MFLOOS');kjBtn.classList.toggle('active',channel==='KJ');
 channelBadge.textContent=channel==='KJ'?'KJ Channel':'MFloos Channel';channelHint.textContent=channel==='KJ'?'Kuraimi Express fee configuration':'MFloos fee configuration';mappingTitle.textContent=channel==='KJ'?'KJ mappings':'MFloos mappings';
 await loadProducts();await loadZones();currencyChanged();await renderMappings();result.classList.add('hidden');error.textContent='';
}
async function loadProducts(){
 const ps=await fetch(`/api/channel/${channel}/products`).then(r=>r.json());
 product.innerHTML=ps.map(p=>`<option value="${p.PROD_ID}">${p.PROD_NAME} (${p.PROD_ID})</option>`).join('');
 if(channel==='MFLOOS')product.insertAdjacentHTML('afterbegin','<option value="">Select product</option>');
 product.disabled=(channel==='KJ'&&ps.length===1);if(channel==='KJ'&&ps.length===1)product.value=ps[0].PROD_ID;
 await loadTransactions();
}
async function loadTransactions(){
 transaction.innerHTML='<option value="">Select transaction</option>';if(!product.value)return;
 const ts=await fetch(`/api/channel/${channel}/transactions/${product.value}`).then(r=>r.json());
 transaction.innerHTML+=ts.map(t=>`<option value="${t.TRAN_ID}">${t.TRAN_NAME} (${t.TRAN_ID})</option>`).join('');
}
async function loadZones(){
 const zs=await fetch(`/api/channel/${channel}/zones`).then(r=>r.json());
 const o='<option value="">Select zone</option>'+zs.map(z=>`<option value="${z.ZONE_ID}">${z.ZONE_CODE} (${z.ZONE_NAME})</option>`).join('');
 senderZone.innerHTML=o;receiverZone.innerHTML=o;
}
function currencyChanged(){const f=currency.value!=='YER';liquidityFields.classList.toggle('hidden',f);zoneFields.classList.toggle('hidden',!f);modeNote.textContent=!f?'YER uses the liquidity-based calculation.':channel==='KJ'?'KJ SAR/USD uses LQDTY 00004 (No Liquidity) + Extra Commission.':'MFloos SAR/USD uses High Fee (LQDTY 00001) + Extra Commission.'}
async function calculate(){
 error.textContent='';result.classList.add('hidden');
 const b={channel,productId:product.value,transactionId:transaction.value,currency:currency.value,amount:Number(amount.value),fromLiquidity:fromLiq.value,toLiquidity:toLiq.value,senderZoneId:senderZone.value,receiverZoneId:receiverZone.value};
 if(!b.productId||!b.transactionId){error.textContent='Select both Product and Transaction.';return}
 const res=await fetch('/api/calculate',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(b)}),d=await res.json();
 if(!res.ok){error.textContent=d.error||'Calculation failed.';return}
 trace.innerHTML=`<span class="chip">${channel==='KJ'?'KJ':'MFloos'}</span><span class="arrow">→</span><span class="chip">${d.productName}</span><span class="arrow">→</span><span class="chip">${d.transactionName}</span><span class="arrow">→</span><span class="chip">${d.currency}</span><span class="arrow">→</span><span class="chip">Group ${d.feeGroupId}</span><span class="arrow">→</span><span class="chip">Fee ${d.feeId}</span>`;
 if(d.mode==='YER'){
  yerMetrics.classList.remove('hidden');fxMetrics.classList.add('hidden');yerDetails.classList.remove('hidden');fxDetails.classList.add('hidden');
  highValue.textContent=`${money(d.high.fee)} YER`;calcValue.textContent=`${money(d.calculated.fee)} YER`;finalValue.textContent=`${money(d.finalFee)} YER`;
  highSub.textContent=`Raw ${money(d.high.raw)} · ${d.high.percentage}%`;calcSub.textContent=`${d.calculatedLiquidity} · Raw ${money(d.calculated.raw)} · ${d.calculated.percentage}%`;finalSub.textContent=`${money(d.calculated.fee)} − ${money(d.high.fee)}`;
  highPct.textContent=d.high.percentage+'%';highRange.textContent=`${money(d.high.rangeStart)} – ${money(d.high.rangeEnd)}`;highMinMax.textContent=`${money(d.high.minFee)} / ${money(d.high.maxFee)}`;highCap.textContent=d.high.capApplied;
  calcPct.textContent=d.calculated.percentage+'%';calcRange.textContent=`${money(d.calculated.rangeStart)} – ${money(d.calculated.rangeEnd)}`;calcMinMax.textContent=`${money(d.calculated.minFee)} / ${money(d.calculated.maxFee)}`;calcCap.textContent=d.calculated.capApplied;
  formula.textContent=`Final Liquidity Fee = ${money(d.calculated.fee)} - ${money(d.high.fee)} = ${money(d.finalFee)} YER`;
 }else{
  yerMetrics.classList.add('hidden');fxMetrics.classList.remove('hidden');yerDetails.classList.add('hidden');fxDetails.classList.remove('hidden');
  foreignFeeLabel.textContent=channel==='KJ'?'Transaction Fee':'High Fee';foreignRuleTitle.textContent=channel==='KJ'?'Transaction fee rule':'High fee rule';
  fxFeeValue.textContent=`${money(d.transactionFee.fee)} ${d.currency}`;extraValue.textContent=`${money(d.extraCommission)} ${d.currency}`;totalValue.textContent=`${money(d.totalFee)} ${d.currency}`;
  fxFeeSub.textContent=`Raw ${money(d.transactionFee.raw)} · ${d.transactionFee.percentage}%`;extraSub.textContent=`Sender ${d.senderPercentage}% − Receiver ${d.receiverPercentage}%`;totalSub.textContent=`${money(d.transactionFee.fee)} + ${money(d.extraCommission)}`;
  foreignLiqCode.textContent=d.foreignLiquidityCode+(channel==='KJ'?' (No Liquidity)':' (High)');fxPct.textContent=d.transactionFee.percentage+'%';fxRange.textContent=`${money(d.transactionFee.rangeStart)} – ${money(d.transactionFee.rangeEnd)}`;fxMinMax.textContent=`${money(d.transactionFee.minFee)} / ${money(d.transactionFee.maxFee)}`;fxCap.textContent=d.transactionFee.capApplied;
  senderPctOut.textContent=d.senderPercentage+'%';receiverPctOut.textContent=d.receiverPercentage+'%';rawExtra.textContent=`${money(d.rawExtraCommission)} ${d.currency}`;extraApplied.textContent=`${money(d.extraCommission)} ${d.currency}`;
  formula.textContent=`Total Fee = Transaction Fee + Extra Commission = ${money(d.transactionFee.fee)} + ${money(d.extraCommission)} = ${money(d.totalFee)} ${d.currency}`;
 }
 result.classList.remove('hidden');
}
function showTab(id){document.querySelectorAll('.tab').forEach(b=>b.classList.toggle('active',b.dataset.tab===id));document.querySelectorAll('.pane').forEach(p=>p.classList.toggle('active',p.id===id))}
async function renderMappings(){
 const rows=await fetch(`/api/channel/${channel}/mappings`).then(r=>r.json());
 mappingBody.innerHTML=rows.map(x=>`<tr><td>${x.PROD_NAME}</td><td>${x.TRAN_NAME}</td><td>${x.FEE_GROUP_ID}</td><td>${x.FEES.USD.length?`<span class="ok">${x.FEES.USD[0]}</span>`:'<span class="bad">No config</span>'}</td><td>${x.FEES.YER.length?`<span class="ok">${x.FEES.YER[0]}</span>`:'<span class="bad">No config</span>'}</td><td>${x.FEES.SAR.length?`<span class="ok">${x.FEES.SAR[0]}</span>`:'<span class="bad">No config</span>'}</td><td>${x.EXTRA_CMSN_ID}</td></tr>`).join('');
}
document.addEventListener('DOMContentLoaded',()=>{
 mfBtn.addEventListener('click',()=>setChannel('MFLOOS'));kjBtn.addEventListener('click',()=>setChannel('KJ'));product.addEventListener('change',loadTransactions);currency.addEventListener('change',currencyChanged);calculateBtn.addEventListener('click',calculate);document.querySelectorAll('.tab').forEach(b=>b.addEventListener('click',()=>showTab(b.dataset.tab)));setChannel('MFLOOS');
});
