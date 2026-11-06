/* Homepage summary: presentation only; no model calculations or alert triggers. */
(()=>{
'use strict';
const $=id=>document.getElementById(id);
const set=(id,value)=>{const el=$(id);if(el)el.textContent=value};
const num=v=>v!==null&&v!==undefined&&v!==''&&Number.isFinite(Number(v))?Number(v):null;
async function init(){
 try{
  const response=await fetch('./data/report.json?overview='+Date.now(),{cache:'no-store'});
  if(!response.ok)throw Error('HTTP '+response.status);
  const data=await response.json(),rows=Array.isArray(data.rows)?data.rows:[];
  const valid=rows.filter(r=>r.swing&&r.data_quality?.status!=='blocked');
  const verified=valid.filter(r=>r.data_quality?.status==='ok');
  const flagged=valid.filter(r=>r.data_quality?.status==='warning');
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
  const iidStrong=valid.filter(r=>[10,15,20].some(n=>{
   const b=r.stage2?.backtests?.[String(n)];
   const ci=b?.mean_net_bootstrap_ci95_pct;
   return Array.isArray(ci)&&num(ci[0])!==null&&num(ci[0])>0;
  }));
  set('homepage-asof','資料生成：'+(data.updated_utc||'日期待確認'));
  if(!rows.length||!rows.some(r=>r.swing)){
   set('homepage-opportunity-value','資料待更新');
   set('homepage-opportunity-desc','尚未取得有效五維研究資料，請先核對每日更新。');
  }else{
   set('homepage-opportunity-value',candidates.length+' 隻優先研究');
   set('homepage-opportunity-desc','另有 '+watched.length+' 隻觀察名單；其中 '+candidates.filter(r=>r.data_quality?.status==='warning').length+' 隻優先研究有行情警告。有效研究股票 '+valid.length+' 隻。');
  }
  set('homepage-risk-value',regime);
  set('homepage-risk-desc','大市研究分類｜行情品質待查 '+qualityIssues+' 隻；財報日期未確認 '+missingEarnings+' 隻。');
  set('homepage-evidence-value',evidence.length+' / '+valid.length+' 隻');
  set('homepage-evidence-desc','ATR 策略三個持有期均有至少30筆交易：'+evidence.length+' 隻；任一持有期 IID Bootstrap 95% 區間下限高於零：'+iidStrong.length+' 隻。與五維核心策略不同，且未校正多重比較。');
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