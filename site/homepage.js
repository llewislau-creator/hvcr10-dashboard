/* Homepage summary: presentation only; no model calculations or alert triggers. */
(()=>{
'use strict';
const $=id=>document.getElementById(id);
const set=(id,value)=>{const el=$(id);if(el)el.textContent=value};
const num=v=>Number.isFinite(Number(v))?Number(v):null;
async function init(){
 try{
  const response=await fetch('./data/report.json?overview='+Date.now(),{cache:'no-store'});
  if(!response.ok)throw Error('HTTP '+response.status);
  const data=await response.json(),rows=Array.isArray(data.rows)?data.rows:[];
  const valid=rows.filter(r=>r.swing&&r.data_quality?.status==='ok');
  const candidates=valid.filter(r=>r.swing?.signal==='優先研究');
  const watched=valid.filter(r=>r.swing?.signal==='觀察名單');
  const qualityIssues=rows.filter(r=>r.data_quality?.status!=='ok').length+(data.coverage?.excluded?.length||0);
  const missingEarnings=rows.filter(r=>!r.earnings?.date||r.earnings?.status==='unknown').length;
  const market=data.phase1?.market||{};
  const regime=typeof market.regime==='string'&&market.regime.trim()?market.regime:'尚未確認';
  const evidence=valid.filter(r=>{
   const periods=r.stage2?.backtests||{};
   return [10,15,20].every(n=>{
    const b=periods[String(n)];
    return b&&num(b.n)!==null&&num(b.n)>=30&&num(b.mean_net_pct)!==null&&num(b.profit_factor)!==null;
   });
  });
  const passed=evidence.filter(r=>[10,15,20].every(n=>{
   const b=r.stage2.backtests[String(n)];
   return Number(b.mean_net_pct)>0&&Number(b.profit_factor)>=1;
  }));
  set('homepage-asof','資料生成：'+(data.updated_utc||'日期待確認'));
  if(!rows.length||!rows.some(r=>r.swing)){
   set('homepage-opportunity-value','資料待更新');
   set('homepage-opportunity-desc','尚未取得有效五維研究資料，請先核對每日更新。');
  }else{
   set('homepage-opportunity-value',candidates.length+' 隻優先研究');
   set('homepage-opportunity-desc','另有 '+watched.length+' 隻觀察名單；有效研究股票 '+valid.length+' 隻。非買入建議。');
  }
  set('homepage-risk-value',regime);
  set('homepage-risk-desc','大市研究分類｜行情品質待查 '+qualityIssues+' 隻；財報日期未確認 '+missingEarnings+' 隻。');
  set('homepage-evidence-value',evidence.length+' / '+valid.length+' 隻');
  set('homepage-evidence-desc','三個持有期樣本均達 30 筆且具備績效資料；其中 '+passed.length+' 隻三期均達研究門檻。非機率校準。');
 }catch(error){
  set('homepage-asof','資料尚未載入');
  for(const id of ['homepage-opportunity-value','homepage-risk-value','homepage-evidence-value'])set(id,'資料不可用');
  set('homepage-opportunity-desc','請核對每日研究報告是否成功更新。');
  set('homepage-risk-desc','無法確認最新市場風險，請勿將空白視為低風險。');
  set('homepage-evidence-desc','無法核對樣本外研究證據。');
 }
}
if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',init);else init();
})();