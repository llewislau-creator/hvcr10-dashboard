
const $=id=>document.getElementById(id),esc=x=>String(x??'—').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));let all=[];
const fmt=(x,suffix='')=>x==null?'—':esc(x)+suffix;
const stat=(k,v,n)=>'<div class="stat"><small>'+esc(k)+'</small><b>'+esc(v)+'</b><small>'+esc(n)+'</small></div>';
function rank(){let s=$('sort').value,query=($('search-ticker')?.value||'').trim().toUpperCase(),filter=$('filter-status')?.value||'all',rows=all.filter(r=>r.ticker.toUpperCase().includes(query)&&(filter==='all'||(filter==='priority'?r.swing?.signal==='優先研究':r.swing?.signal==='觀察名單')));rows.sort((a,b)=>{let x=a.swing||{},y=b.swing||{};if(s==='ticker')return a.ticker.localeCompare(b.ticker);if(s==='mom')return (y.momentum_20d_pct??-999)-(x.momentum_20d_pct??-999);if(s==='relative')return (y.relative_spy_20d_pct??-999)-(x.relative_spy_20d_pct??-999);return Number(y.eligible)-Number(x.eligible)||(y.score??-1)-(x.score??-1)||(y.liquidity_dollar_m??0)-(x.liquidity_dollar_m??0)||a.ticker.localeCompare(b.ticker)});
$('rows').innerHTML=rows.map((r,i)=>{let s=r.swing||{},h=s.holdout?.['10']||{};return '<tr><td>#'+(i+1)+'</td><td><button data-t="'+esc(r.ticker)+'">'+esc(r.ticker)+'</button></td><td>$'+fmt(r.close)+'</td><td>'+fmt(s.score,'/100')+'</td><td class="'+(s.signal==='優先研究'?'good':'muted')+'">'+esc(s.signal||'待更新')+'</td><td>'+esc(r.phase1_risk||'待更新')+'</td><td>'+esc(r.data_quality?.status||'待更新')+'</td><td>'+fmt(s.momentum_20d_pct,'%')+'</td><td>'+fmt(s.relative_spy_20d_pct,'%')+'</td><td>'+fmt(h.mean_net_pct,'%')+'</td><td>'+fmt(h.n)+'</td><td>'+esc(r.last_price_date)+'</td></tr>'}).join('');document.querySelectorAll('[data-t]').forEach(b=>b.onclick=()=>{if(document.body.dataset.page==='screener'){location.href='./stock.html?ticker='+encodeURIComponent(b.dataset.t)}else{$('ticker').value=b.dataset.t;detail()}})}
function researchEvidence(r){
 const q=r.data_quality||{},bt=r.stage2?.backtests||{};
 const quality=q.status==='ok'?'完整':q.status==='warning'?'有警告':'未驗證';
 const detail=[10,15,20].map(n=>{
  const b=bt[String(n)];
  if(!b||!Number.isFinite(b.n))return n+'日：未提供';
  return n+'日：'+b.n+'筆';
 }).join('；');
 const sample=[10,15,20].every(n=>Number.isFinite(bt[String(n)]?.n)&&bt[String(n)].n>=30)?'三個持有期均達30筆':'樣本未全數達標';
 const pass=n=>{const b=bt[String(n)];return b&&Number.isFinite(b.mean_net_pct)&&Number.isFinite(b.profit_factor)&&b.mean_net_pct>0&&b.profit_factor>=1};
 const complete=[10,15,20].every(n=>{const b=bt[String(n)];return b&&Number.isFinite(b.mean_net_pct)&&Number.isFinite(b.profit_factor)&&Number.isFinite(b.n)&&b.n>=30});
 const performance=!complete?'證據不足':([10,15,20].every(pass)?'三期均達門檻':'未全數通過');
 return '<h3>研究證據分項檢視（非買入機率）</h3><div class="grid">'+
 stat('行情資料完整性',quality,(q.issues||[]).join('；')||'沒有已知品質警告')+
 stat('樣本充足程度',sample,detail)+
 stat('樣本外績效門檻',performance,'僅在三期均≥30筆時評估；平均淨報酬>0%、Profit Factor≥1')+
 '</div><p class="muted">三個維度分開判讀，不合成分數、不作交易訊號、不影響排行榜；門檻是研究篩選規則，不是統計顯著性或未來獲利保證。</p>';
}
function riskWarnings(r){
 const bt=r.stage2?.backtests||{},warnings=[];
 if(r.data_quality?.status!=='ok')warnings.push('行情品質警告：'+(r.data_quality?.issues||[]).join('；'));
 if(r.earnings?.status==='unknown')warnings.push('財報日期尚未確認');
 for(const n of [10,15,20]){
  const b=bt[String(n)];
  if(!b||!Number.isFinite(b.n)){warnings.push(n+'日回測資料缺失');continue}
  if(b.n<30)warnings.push(n+'日樣本不足：'+b.n+'筆（最低30筆）');
  if(b.mean_net_pct==null||b.profit_factor==null)warnings.push(n+'日績效指標不足');
  else if(b.mean_net_pct<=0||b.profit_factor<1)warnings.push(n+'日樣本外績效偏弱：平均淨報酬不正或Profit Factor低於1');
 }
 return warnings;
}
function forwardEvidence(s){
 const bt=s?.backtests||{};
 const items=[10,15,20].map(n=>{
  const b=bt[String(n)]||{},wf=b.walk_forward,folds=wf?.folds||[];
  const foldText=folds.length===3?folds.map(f=>{
   const ci=f.n>=30?'樣本達標':'樣本不足';
   return '第'+f.fold+'段：'+f.n+'筆／'+ci+'／平均淨報酬'+fmt(f.mean_net_pct,'%');
  }).join('；'):'等待新版Walk-forward報告';
  const bear=b.regime_results?.['SPY下降趨勢']?.n||0;
  const bearLabel=bear>=30?'熊市樣本數達標（仍需驗證績效）':'熊市穩健性未驗證（'+bear+'/30筆）';
  const ci=b.mean_net_bootstrap_ci95_pct;
  const ciLabel=Array.isArray(ci)&&ci[0]>0?'區間支持正報酬（描述性）':'未獲得正報酬區間支持';
  return '<div class="stat"><small>'+n+'日｜分段研究證據</small><b>'+esc(bearLabel)+'</b><small>'+esc(foldText)+'</small><small>'+esc(ciLabel)+'</small></div>';
 }).join('');
 return '<h3>Walk-forward 分段證據（獨立判讀）</h3><div class="grid">'+items+'</div><p class="muted">每段30筆門檻不變；熊市樣本30筆只代表覆蓋門檻，並非績效通過。歷史重疊或相關性不等於獨立新證據。固定規則前向驗證不等於重新訓練最佳化。</p>';
}
function robustnessHTML(s){
 if(!s)return '';
 const bt=s.backtests||{};
 const rows=[10,15,20].map(n=>{
  const b=bt[String(n)]||{},ci=b.mean_net_bootstrap_ci95_pct,reg=b.regime_results||{};
  const regime=['SPY上升趨勢','SPY下降趨勢'].map(k=>{const x=reg[k]||{};return esc(k)+': '+fmt(x.n)+'筆 / '+fmt(x.mean_net_pct,'%')}).join('；');
  return '<tr><td>'+n+'日</td><td>'+fmt(b.n)+'</td><td>'+(Array.isArray(ci)?fmt(ci[0])+'% ～ '+fmt(ci[1])+'%':'—')+'</td><td>'+regime+'</td></tr>';
 }).join('');
 return '<h4>樣本外穩健性檢查</h4><div class="scroll"><table><thead><tr><th>持有期</th><th>獨立交易數</th><th>平均淨報酬 Bootstrap 95% 區間</th><th>SPY 市場環境分組</th></tr></thead><tbody>'+rows+'</tbody></table></div><p class="muted">逐筆非重疊交易；2000次固定種子bootstrap。區間未校正序列相關及跨股票相關，並非未來獲利信賴區間。市場環境以訊號當日SPY相對200交易日前的價格判定；小樣本僅供診斷。</p>';
}
function stage2HTML(s){
 if(!s)return '<p class="muted">第二階段資料待每日更新產生。</p>';
 const p=s.plan||{},bt=s.backtests||{};
 const cards=[
 ['參考入場價',fmt(p.reference_entry),'收盤參考，非保證成交'],
 ['ATR(14)',fmt(p.atr14),'價格波幅'],
 ['止損參考',fmt(p.stop),'2 ATR'],
 ['目標參考',fmt(p.target),'2R'],
 ['風險預算',fmt(p.max_risk_budget),'假設本金 USD 10,000'],
 ['參考股數',fmt(p.shares),'單筆風險0.5%；資金上限15%'],
 ['持倉金額',fmt(p.position_capital),'美元']
 ].map(v=>stat(v[0],v[1],v[2])).join('');
 const body=[10,15,20].map(n=>{
 const b=bt[String(n)]||{};
 return '<tr><td>'+n+'日</td><td>'+fmt(b.n)+'</td><td>'+fmt(b.mean_net_pct,'%')+'</td><td>'+fmt(b.win_rate_pct,'%')+'</td><td>'+fmt(b.profit_factor)+'</td><td>'+fmt(b.mean_excess_spy_pct,'%')+'</td><td>'+fmt(b.max_sequential_drawdown_pct,'%')+'</td></tr>';
 }).join('');
 return '<h3>第二階段｜ATR 風險計劃及樣本外回測</h3><p class="notice">研究參考，非買入訊號；不保證成交。回測不參與排行榜排序。</p><div class="grid">'+cards+'</div><div class="scroll"><table><thead><tr><th>持有期</th><th>交易數</th><th>平均淨報酬</th><th>淨勝率</th><th>Profit Factor</th><th>相對 SPY</th><th>最大序列回撤</th></tr></thead><tbody>'+body+'</tbody></table></div><p class="muted">樣本外後30%歷史；下一日開盤入場，止損優先；每邊成本15bps及滑價10bps。過去績效不代表未來。</p>';
}

let portfolioData=null;
function quickOverview(){
 const eligible=all.filter(r=>r.swing?.signal==='優先研究');
 const quality=all.filter(r=>r.data_quality?.status!=='ok');
 const uncertain=all.filter(r=>r.earnings?.status==='unknown'||!r.earnings?.date);
 $('quick-overview').innerHTML=stat('優先研究候選',eligible.length,'依五維研究分數，非買入訊號')+stat('行情品質警告',quality.length,'不含已隔離股票')+stat('財報日期未確認',uncertain.length,'不代表近期沒有財報')+stat('研究股票數',all.length,'先看證據，再判斷風險');
 const items=[...eligible].sort((a,b)=>(b.swing?.score??0)-(a.swing?.score??0)).slice(0,6);
 $('quick-list').innerHTML=items.length?'<table><thead><tr><th>股票</th><th>研究分數</th><th>資料品質</th><th>財報</th><th>10日回測樣本</th><th>證據</th></tr></thead><tbody>'+items.map(r=>{
 const b=r.stage2?.backtests?.['10']||{},enough=Number.isFinite(b.n)&&b.n>=30;
 const quality=r.data_quality?.status==='ok'?'正常':'待查';
 const evidence=!enough?'樣本不足':b.mean_net_pct>0&&b.profit_factor>=1?'達研究門檻':'未達研究門檻';
 return '<tr><td>'+esc(r.ticker)+'</td><td>'+fmt(r.swing?.score,'/100')+'</td><td>'+esc(quality)+'</td><td>'+esc(r.earnings?.date||'待確認')+'</td><td>'+fmt(b.n)+'</td><td>'+esc(evidence)+'</td></tr>';
 }).join('')+'</tbody></table>':'<p class="muted">目前沒有符合優先研究條件的股票。</p>';
}
function lineChart(data,drawdown=false){
 const pts=(data||[]).filter(d=>Number.isFinite(Number(d.equity))&&Number(d.equity)>0);
 if(pts.length<2)return '<p class="muted">暫無足夠每日權益數據可繪圖。</p>';
 let peak=Number(pts[0].equity),vals=pts.map(d=>{let v=Number(d.equity);peak=Math.max(peak,v);return drawdown?(v/peak-1)*100:v});
 const low=Math.min(...vals),high=Math.max(...vals),span=Math.max(high-low,0.0001),W=720,H=218,pad=18;
 const path=vals.map((v,i)=>(i?'L':'M')+(pad+i*(W-2*pad)/(vals.length-1)).toFixed(2)+','+(pad+(high-v)*(H-2*pad)/span).toFixed(2)).join(' ');
 const color=drawdown?'#FF7185':'#59A9FF';
 return '<svg viewBox="0 0 '+W+' '+H+'" role="img" aria-label="'+(drawdown?'組合歷史回撤曲線':'組合歷史權益曲線')+'" preserveAspectRatio="none"><line x1="18" y1="200" x2="702" y2="200" stroke="#34455E"/><line x1="18" y1="109" x2="702" y2="109" stroke="#34455E" stroke-dasharray="4 7"/><path d="'+path+'" fill="none" stroke="'+color+'" stroke-width="2.5" vector-effect="non-scaling-stroke"/></svg><div class="chart-axis"><span>'+esc(pts[0].date)+'</span><span>'+esc(drawdown?low.toFixed(1)+'%':Math.round(low).toLocaleString()+'–'+Math.round(high).toLocaleString())+'</span><span>'+esc(pts[pts.length-1].date)+'</span></div>';
}
function renderPortfolio(){
 if(!portfolioData)return;
 const p=portfolioData.portfolios?.[$('portfolio-horizon').value];
 if(!p){$('portfolio-status').textContent='此持有期沒有組合研究資料';return}
 $('portfolio-status').textContent='研究資料生成時間：'+portfolioData.updated_utc+'｜研究狀態：'+(p.status==='research_only'?'僅供研究':p.status);
 $('portfolio-summary').innerHTML=stat('最大回撤',fmt(p.max_drawdown_pct,'%'),'歷史組合權益最大跌幅')+stat('年化波動率',fmt(p.annualized_volatility_pct,'%'),'每日組合報酬估算')+stat('平均資金曝險',fmt(p.mean_exposure_pct,'%'),'最高 '+fmt(p.max_exposure_pct,'%'))+stat('最大同期持倉',fmt(p.max_concurrent_positions),'模擬執行 '+fmt(p.trades_executed)+' 筆')+stat('平均股票相關性',fmt(p.stock_correlation?.mean_pairwise_daily_return_correlation),'符合門檻 '+fmt(p.stock_correlation?.pair_count)+' 對')+stat('跳過交易',fmt(p.trades_skipped),'資金不足或已持有等原因');
 $('equity-chart').innerHTML=lineChart(p.daily_equity,false);$('drawdown-chart').innerHTML=lineChart(p.daily_equity,true);const regime=p.market_regime||{};
 $('portfolio-regime').innerHTML='<h3>SPY 趨勢分組（平均每日報酬）</h3><div class="grid">'+[['SPY_above_200d','SPY 高於 200 日前收盤價'],['SPY_not_above_200d','SPY 不高於 200 日前收盤價']].map(([k,label])=>stat(label,fmt(regime[k]?.mean_daily_return_pct,'%'),fmt(regime[k]?.days)+' 日')).join('')+'</div>';
}
async function loadPortfolio(){
 try{
 const res=await fetch('./data/portfolio_risk.json?x='+Date.now(),{cache:'no-store'});
 if(!res.ok)throw Error('HTTP '+res.status);
 portfolioData=await res.json();
 renderPortfolio();
 }catch(e){$('portfolio-status').textContent='組合風險資料讀取失敗：'+e.message}
}
$('portfolio-horizon').onchange=renderPortfolio;
loadPortfolio();
function detail(){let r=all.find(x=>x.ticker===$('ticker').value);if(!r)return;$('research-confidence').innerHTML=researchEvidence(r);const warnings=riskWarnings(r);$('risk-warnings').innerHTML=warnings.length?'<div class="notice"><b>風險警示（'+warnings.length+'項）</b>'+warnings.map(w=>'<p>⚠ '+esc(w)+'</p>').join('')+'</div>':'<p class="muted">未觸發預設風險警示；不代表沒有投資風險。</p>';$('stage2').innerHTML=stage2HTML(r.stage2);$('robustness').innerHTML=robustnessHTML(r.stage2);$('forward-evidence').innerHTML=forwardEvidence(r.stage2);let s=r.swing||{},f=s.factors||{};let factors=Object.entries(f).map(([k,v])=>'<span class="pill '+(v?'good':'')+'">'+(v===null?'? ':v?'✓ ':'✕ ')+esc(k)+'</span>').join('');
let back=[10,15,20].map(n=>{let h=s.holdout?.[n]||{};return '<tr><td>'+n+'日</td><td>'+fmt(h.n)+'</td><td>'+fmt(h.mean_net_pct,'%')+'</td><td>'+fmt(h.positive_net_pct,'%')+'</td><td>'+fmt(h.mean_excess_spy_pct,'%')+'</td><td>'+fmt(h.min_net_pct,'%')+'</td></tr>'}).join('');
$('detail').innerHTML='<div class="grid">'+stat('財報日期',r.earnings?.date||'待確認',r.earnings?.note||'尚未更新')+stat('數據品質',r.data_quality?.status||'待更新',(r.data_quality?.issues||[]).join('；')||'未偵測到品質問題')+stat('研究分數',fmt(s.score,'/100'),'非成功機率')+stat('研究狀態',s.signal||'待更新','僅供研究')+stat('20日動能',fmt(s.momentum_20d_pct,'%'),'價格變化')+stat('60日動能',fmt(s.momentum_60d_pct,'%'),'中期趨勢')+stat('相對SPY',fmt(s.relative_spy_20d_pct,'%'),'20日相對表現')+stat('20日平均成交額',fmt(s.liquidity_dollar_m,' 百萬美元'),'流動性參考')+'</div><h3>五維因素</h3>'+factors+'<h3>10／15／20 日樣本外持有期研究</h3><div class="scroll"><table><thead><tr><th>持有期</th><th>事件數</th><th>平均淨報酬</th><th>淨報酬為正比例</th><th>平均超越SPY</th><th>最差單筆淨報酬</th></tr></thead><tbody>'+back+'</tbody></table></div><p class="muted">單一股票歷史非重疊事件；樣本少時不應據此推斷未來表現。</p>'}
async function load(){try{let res=await fetch('./data/report.json?x='+Date.now(),{cache:'no-store'});if(!res.ok)throw Error('HTTP '+res.status);let d=await res.json();all=d.rows||[];let ready=all.length&&all.every(r=>r.swing);let excluded=d.coverage?.excluded||[];let coverage=d.coverage;let ex=$('exclusions');ex.hidden=!excluded.length;if(excluded.length)ex.innerHTML='<h2>已隔離股票（不參與排名）</h2><p class="warn">本次僅發布通過品質檢查的股票；以下股票未使用舊行情填補。</p>'+excluded.map(x=>'<p><b>'+esc(x.ticker)+'</b>：'+esc(x.reason)+'</p>').join('');let m=d.phase1?.market||{};$('market').innerHTML=stat('市場狀態',m.regime||'待更新','SPY／QQQ 均線判斷')+stat('SPY 20日表現',fmt(m.SPY?.return_20d_pct,'%'),m.SPY?.date||'資料待更新')+stat('QQQ 20日表現',fmt(m.QQQ?.return_20d_pct,'%'),m.QQQ?.date||'資料待更新')+stat('VIX',fmt(m.VIX?.value),m.VIX?.date||'資料待更新')+stat('財報日期待確認',all.filter(r=>r.earnings?.status!=='upcoming').length,'不等於沒有財報');$('health').innerHTML='<b>資料狀態：</b>'+(ready?'<span class="good">波段投資研究資料已載入</span>':'<span class="warn">等待新版每日更新產生波段資料</span>')+'　｜<strong class="warn">回測／組合風險：待獨立核對（非實盤）</strong>'+'　｜生成時間：'+esc(d.updated_utc)+'　｜有效股票：'+all.length+(coverage?'／'+esc(coverage.expected)+'（'+esc(coverage.pct)+'%）':'　｜覆蓋率未提供');
if(!ready){$('rows').innerHTML='<tr><td colspan="12">請執行 GitHub Actions 每日更新以產生新版波段數據。</td></tr>';return}
$('summary').innerHTML=stat('已驗證股票',all.length,'候選20隻；不合格股票排除')+stat('優先研究',all.filter(r=>r.swing.signal==='優先研究').length,'觀察分數≥80且流動性合格')+stat('觀察名單',all.filter(r=>r.swing.signal==='觀察名單').length,'觀察分數≥60且流動性合格')+stat('投資週期','10／15／20日','約2–4星期')+stat('校準機率','尚未提供','不捏造勝率');
$('ticker').innerHTML=all.map(r=>'<option>'+esc(r.ticker)+'</option>').join('');const requested=new URLSearchParams(location.search).get('ticker');if(requested&&all.some(r=>r.ticker===requested))$('ticker').value=requested;rank();detail();quickOverview()}catch(e){$('health').textContent='讀取失敗：'+e.message}}
$('search-ticker').oninput=rank;$('filter-status').onchange=rank;$('sort').onchange=rank;$('ticker').onchange=detail;load();
