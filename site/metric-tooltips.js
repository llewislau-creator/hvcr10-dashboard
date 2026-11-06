/* Accessible table-header explanations: hover on desktop, tap on mobile. */
(()=>{
'use strict';
const help={
'排名':'按照目前所選排序條件排列的名次，並非預測股價漲幅。',
'股票':'美股交易代號（Ticker），點選股票可查看個股研究。',
'價格':'最近一次取得的收盤價格；請以行情日期核對資料新鮮度。',
'波段分數':'五個技術條件各佔20分，總分0至100。不是上漲機率或買入指令。',
'研究分數':'五個技術條件各佔20分，總分0至100。不是上漲機率或買入指令。',
'研究狀態':'依流動性及五維分數分類為優先研究、觀察名單或暫不優先，不是交易建議。',
'財報風險':'財報發布前後股價可能跳空；日期待確認不代表近期沒有財報。',
'數據品質':'檢查價格、成交量及資料完整性；異常或缺漏可能影響研究結果。',
'20日動能':'最近20個交易日的價格報酬率，計算為最新收盤價除以20日前收盤價再減1。',
'相對SPY':'股票最近20日報酬率減去SPY同期報酬率。正值代表同期跑贏標普500指數代理ETF。',
'相對 SPY':'股票最近20日報酬率減去SPY同期報酬率。正值代表同期跑贏標普500指數代理ETF。',
'10日樣本外平均淨報酬':'使用未參與原始規則設計的較晚歷史資料，模擬持有10個交易日，扣除假設交易成本後的平均每筆報酬；不代表未來收益。',
'樣本數':'進入該項回測統計的有效歷史交易事件筆數；筆數少代表不確定性較高。',
'行情日':'這筆行情對應的交易日期，與網站開啟日期可能不同。',
'事件數':'符合研究條件並進入回測統計的交易事件數量。',
'平均淨報酬':'扣除模型設定的交易成本與滑價後，每筆歷史模擬交易的平均報酬。',
'淨報酬為正比例':'歷史模擬交易中，扣除假設成本後仍為正報酬的比例。',
'平均超越SPY':'模擬策略報酬減去同期SPY基準報酬的平均差額。',
'最差單筆淨報酬':'回測樣本中最差一筆交易的扣費後報酬。',
'勝率':'獲利交易筆數除以總交易筆數；勝率高不保證整體獲利。',
'Profit Factor':'總獲利除以總虧損絕對值；大於1表示樣本內獲利總額高於虧損總額。',
'最大序列回撤':'歷史模擬資產淨值從前高到其後低點的最大跌幅。',
'持有期':'模擬進場至出場之間的交易日數，不包括休市日。',
'股票代號':'股票在交易所使用的識別代碼。',
'研究分數 /100':'由五個技術條件構成的研究評分，並非上漲機率。'
};
const norm=s=>s.replace(/\s+/g,'').replace(/[（）()]/g,'').trim();
const lookup=s=>help[s.trim()]||Object.entries(help).find(([k])=>norm(k)===norm(s))?.[1]||null;
let pop,active=null,pinned=false;
const css=document.createElement('style');css.textContent='.metric-help-header{cursor:help;position:relative}.metric-help-header .metric-help-icon{display:inline-flex;vertical-align:middle;align-items:center;justify-content:center;width:17px;height:17px;margin-left:5px;border:1px solid #6695b8;border-radius:50%;color:#9ed8ff;font-size:11px;font-weight:750;line-height:1}.metric-help-header:hover .metric-help-icon,.metric-help-header:focus-visible .metric-help-icon{background:#31648a;color:#fff}.metric-help-pop{position:fixed;z-index:9999;width:min(315px,calc(100vw - 24px));padding:13px 15px;background:#19334b;color:#edf7ff;border:1px solid #70a9cf;border-radius:12px;box-shadow:0 15px 40px #000a;pointer-events:none;text-align:left;white-space:normal;line-height:1.6}.metric-help-pop strong{display:block;font-size:13px;margin-bottom:5px}.metric-help-pop p{margin:0;color:#c5d9e9;font-size:12px}.metric-help-header:focus-visible{outline:2px solid #8ad1ff;outline-offset:-2px}@media(hover:none){.metric-help-pop{pointer-events:auto}.metric-help-header .metric-help-icon{width:19px;height:19px}}';document.head.append(css);
function create(){if(pop)return;pop=document.createElement('div');pop.className='metric-help-pop';pop.id='metric-help-pop';pop.setAttribute('role','tooltip');pop.hidden=true;document.body.append(pop)}
function position(el){const r=el.getBoundingClientRect(),w=pop.offsetWidth,h=pop.offsetHeight;let x=Math.max(12,Math.min(window.innerWidth-w-12,r.left)),y=r.bottom+9;if(y+h>window.innerHeight-12)y=Math.max(12,r.top-h-9);pop.style.left=x+'px';pop.style.top=y+'px'}
function show(el,lock=false){if(!el?.dataset?.metricHelp)return;create();if(active&&active!==el)active.removeAttribute('aria-describedby');active=el;pinned=lock;pop.replaceChildren();const title=document.createElement('strong');title.textContent=el.dataset.metricLabel;const body=document.createElement('p');body.textContent=el.dataset.metricHelp;pop.append(title,body);pop.hidden=false;el.setAttribute('aria-describedby',pop.id);position(el)}
function hide(force=false){if(pinned&&!force)return;if(active)active.removeAttribute('aria-describedby');active=null;pinned=false;if(pop)pop.hidden=true}
function decorate(root){root.querySelectorAll('th').forEach(th=>{if(th.dataset.metricHelp)return;const name=th.textContent.trim(),desc=lookup(name);if(!desc)return;th.dataset.metricHelp=desc;th.dataset.metricLabel=name;th.classList.add('metric-help-header');th.tabIndex=0;th.setAttribute('aria-label',name+'，可查看指標說明');const icon=document.createElement('span');icon.className='metric-help-icon';icon.setAttribute('aria-hidden','true');icon.textContent='?';th.append(icon)})}
document.addEventListener('mouseover',e=>{const th=e.target.closest?.('th.metric-help-header');if(th&&!pinned)show(th)});
document.addEventListener('mouseout',e=>{if(e.target.closest?.('th.metric-help-header')&&!pinned)hide()});
document.addEventListener('focusin',e=>{const th=e.target.closest?.('th.metric-help-header');if(th)show(th)});
document.addEventListener('focusout',e=>{if(e.target.closest?.('th.metric-help-header')&&!pinned)hide()});
document.addEventListener('click',e=>{const th=e.target.closest?.('th.metric-help-header');if(th){if(active===th&&pinned)hide(true);else show(th,true)}else if(!e.target.closest?.('.metric-help-pop'))hide(true)});
document.addEventListener('keydown',e=>{if(e.key==='Escape')hide(true);if((e.key==='Enter'||e.key===' ')&&e.target.matches?.('th.metric-help-header')){e.preventDefault();if(active===e.target&&pinned)hide(true);else show(e.target,true)}});
window.addEventListener('scroll',()=>{if(active&&!pop.hidden)position(active)},true);
window.addEventListener('resize',()=>{if(active&&!pop.hidden)position(active)});
let scheduled=false;function init(){const root=document.querySelector('main')||document.body;decorate(root);new MutationObserver(m=>{if(scheduled||!m.some(x=>Array.from(x.addedNodes).some(n=>n.nodeType===1&&n!==pop)))return;scheduled=true;queueMicrotask(()=>{scheduled=false;decorate(root)})}).observe(root,{childList:true,subtree:true})}
if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',init);else init();
})();