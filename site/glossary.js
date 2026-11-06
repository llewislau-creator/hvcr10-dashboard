/* AlphaLens glossary: click-to-explain terms with small illustrative diagrams. */
(()=>{
'use strict';
const entries=[
['Walk-forward','依時間先後分段測試：只使用較早的資料形成規則，再用較晚資料檢查表現。','timeline'],
['樣本外','沒有用於制定或調整規則的歷史資料；仍不等於未來實盤。','timeline'],
['Profit Factor','獲利交易的總獲利 ÷ 虧損交易的總虧損絕對值。大於 1 表示該樣本總獲利超過總虧損。','ratio'],
['Bootstrap','對歷史樣本重複重抽樣，估計結果對抽樣波動的敏感程度。','distribution'],
['信賴區間','根據樣本與估計方法形成的不確定性範圍，不是未來獲利保證。','distribution'],
['布林帶','以移動平均線為中心，加減標準差形成上下軌，用來觀察價格相對近期波動的位置。','bands'],
['MACD','由快慢指數移動平均線的差異衡量動能；柱狀圖反映 MACD 與訊號線的差距。','momentum'],
['RSI','相對強弱指標，衡量近期漲跌動能，常用 0–100 刻度；高低值不保證反轉。','gauge'],
['MA100','過去 100 個交易日收盤價的簡單平均，用於觀察中期趨勢。','trend'],
['MA50','過去 50 個交易日收盤價的簡單平均，用於觀察趨勢。','trend'],
['MA20','過去 20 個交易日收盤價的簡單平均。','trend'],
['VIX','市場對標普 500 未來約 30 日波動的隱含預期指標，不直接代表股價方向。','gauge'],
['QQQ','追蹤 Nasdaq-100 指數的 ETF，常用作大型科技股市場參考。','comparison'],
['SPY','追蹤標普 500 指數的 ETF，作為美股大盤比較基準。','comparison'],
['NAV','Net Asset Value，組合淨資產價值；網站顯示的是歷史模擬曲線。','trend'],
['回撤','從先前資產或價格高點下跌的幅度；最大回撤是測試期間最深跌幅。','drawdown'],
['相對強度','股票同期報酬與基準指數報酬之差；高於零表示該期間相對跑贏。','comparison'],
['相對 SPY','股票同期報酬減去 SPY 同期報酬，並非保證未來超額收益。','comparison'],
['量價確認','同時觀察價格方向與成交量是否支持該方向的研究條件。','bars'],
['健康回調','價格仍在中期趨勢之上，但短期沒有過度偏離均線的研究狀態。','bands'],
['中期趨勢','以收盤價、50 日及 100 日均線的排列判斷趨勢方向。','trend'],
['短期動能','觀察近期價格報酬及 MACD 柱狀圖變化的動能條件。','momentum'],
['樣本數','符合研究條件且實際進入統計的觀察筆數；樣本少時結果較不穩定。','bars'],
['勝率','獲利交易筆數占總交易筆數的比例；高勝率不代表期望報酬一定為正。','ratio'],
['滑價','預期成交價與實際成交價的差異，會降低策略淨報酬。','bars'],
['bps','基點，1 bps = 0.01%；例如 15 bps = 0.15%。','ratio'],
['市場狀態','依現有價格、均線、布林帶、量價與相對強弱分類的描述性研究標籤。','trend'],
['趨勢轉弱','目前的技術狀態不再符合健康上升趨勢條件；不代表一定會大跌。','drawdown'],
['高風險拋售','布林帶下緣、異常下跌成交量及相對弱勢等條件共同出現的分類；尚未驗證為可靠提前預警。','bands'],
['五維模型','由中期趨勢、短期動能、相對市場強度、健康回調、量價確認五項組成的規則式評分。','bars'],
['波段分數','五個技術條件的規則式研究分數（0–100），不是上漲機率。','gauge'],
['優先研究','流動性符合條件且五維分數至少 80 的研究標籤；不是買入指令。','gauge'],
['觀察名單','流動性符合條件且五維分數至少 60 的研究標籤；不是買入指令。','gauge'],
['數據品質','檢查行情資料完整性、缺漏或異常；資料合格不代表預測正確。','bars'],
['樣本外平均淨報酬','在樣本外測試期間，扣除模型假設交易成本後的平均每筆報酬。','distribution']
].sort((a,b)=>b[0].length-a[0].length);
const glossary=new Map(entries.map(e=>[e[0],e]));
const pattern=new RegExp(entries.map(e=>e[0].replace(/[.*+?^$()|[\]{}]/g,'\\$&')).join('|'),'gi');
const ignore='button,a,select,option,input,textarea,script,style,code,pre,svg,[contenteditable],.glossary-term,.glossary-modal';
let modal=null;
function diagram(kind){
const base='<svg viewBox="0 0 340 125" role="img" aria-label="概念示意圖，非真實行情" xmlns="http://www.w3.org/2000/svg"><rect width="340" height="125" rx="12" fill="#10243a"/><path d="M18 98H322M18 65H322M18 32H322" stroke="#36516b" stroke-dasharray="3 5"/>';
const line=(points,color='#62b5ff')=>'<polyline fill="none" stroke="'+color+'" stroke-width="3" stroke-linecap="round" stroke-linejoin="round" points="'+points+'"/>';
let content='';
if(kind==='timeline')content='<rect x="22" y="42" width="132" height="43" rx="6" fill="#225b7a"/><rect x="166" y="42" width="152" height="43" rx="6" fill="#34755b"/><text x="88" y="69" fill="white" text-anchor="middle" font-size="14">較早資料</text><text x="242" y="69" fill="white" text-anchor="middle" font-size="14">較晚測試</text>';
else if(kind==='bands')content=line('20,82 65,69 110,78 155,48 200,56 245,39 320,50','#65b5ff')+line('20,52 65,39 110,48 155,18 200,26 245,9 320,20','#617e9d')+line('20,112 65,99 110,108 155,78 200,86 245,69 320,80','#617e9d')+line('20,93 65,88 110,70 155,74 200,44 245,68 320,32','#ffbc70');
else if(kind==='distribution')content='<path d="M20 103 Q75 103 105 76 Q165 -3 220 76 Q250 103 320 103" stroke="#65b5ff" stroke-width="3" fill="#244c6a"/><path d="M110 98V30M220 98V73" stroke="#ffbc70" stroke-dasharray="4 4" stroke-width="2"/>';
else if(kind==='gauge')content='<path d="M85 96 A85 85 0 0 1 255 96" stroke="#34536d" stroke-width="16" fill="none"/><path d="M85 96 A85 85 0 0 1 220 35" stroke="#62b5ff" stroke-width="16" fill="none"/><path d="M170 96L215 52" stroke="#ffbc70" stroke-width="4"/><circle cx="170" cy="96" r="6" fill="white"/>';
else if(kind==='ratio')content='<rect x="48" y="38" width="104" height="38" rx="5" fill="#2e8e78"/><rect x="190" y="38" width="72" height="38" rx="5" fill="#b56a6a"/><text x="100" y="62" text-anchor="middle" fill="white" font-size="13">獲利</text><text x="226" y="62" text-anchor="middle" fill="white" font-size="13">虧損</text>';
else if(kind==='bars')content=[60,38,72,51,83,47,95,64].map((h,i)=>'<rect x="'+(29+i*38)+'" y="'+(111-h)+'" width="21" height="'+h+'" rx="3" fill="'+(i%3?'#529cdb':'#48b39b')+'"/>').join('');
else if(kind==='comparison')content=line('20,91 70,83 120,70 170,77 220,50 270,58 320,22')+line('20,95 70,90 120,86 170,65 220,74 270,61 320,49','#ffbc70');
else if(kind==='drawdown')content=line('20,92 65,67 110,43 155,68 200,108 245,77 290,53 320,64')+'<path d="M110 43V108H200" stroke="#ffbc70" stroke-dasharray="5 4" fill="none"/>';
else if(kind==='momentum')content=line('20,83 60,78 100,92 140,60 180,65 220,37 260,49 320,18')+[22,38,30,56,41,67].map((h,i)=>'<rect x="'+(50+i*43)+'" y="'+(114-h/2)+'" width="17" height="'+(h/2)+'" fill="#468db2"/>').join('');
else content=line('20,98 60,83 100,89 140,59 180,66 220,42 260,48 320,18')+line('20,95 60,91 100,82 140,75 180,65 220,55 260,40 320,34','#ffbc70');
return base+content+'</svg><small>概念示意，並非歷史回測或即時股價</small>';
}
function show(term,trigger){
const [name,description,kind]=glossary.get(term);
if(!modal){modal=document.createElement('dialog');modal.className='glossary-modal';modal.setAttribute('aria-label','專有名詞說明');modal.innerHTML='<div class="glossary-header"><h2></h2><button type="button" class="glossary-close" aria-label="關閉說明">×</button></div><div class="glossary-graphic"></div><p></p>';document.body.append(modal);modal.querySelector('button').onclick=()=>modal.close();modal.addEventListener('click',e=>{if(e.target===modal)modal.close()});}
modal.querySelector('h2').textContent=name;modal.querySelector('p').textContent=description;modal.querySelector('.glossary-graphic').innerHTML=diagram(kind);modal.showModal();modal.querySelector('button').focus();
}
function annotate(root){
const walker=document.createTreeWalker(root,NodeFilter.SHOW_TEXT,{acceptNode(node){if(!node.nodeValue.trim()||!node.parentElement||node.parentElement.closest(ignore))return NodeFilter.FILTER_REJECT;pattern.lastIndex=0;return pattern.test(node.nodeValue)?NodeFilter.FILTER_ACCEPT:NodeFilter.FILTER_REJECT;}});
const nodes=[];while(walker.nextNode())nodes.push(walker.currentNode);
for(const node of nodes){const text=node.nodeValue,frag=document.createDocumentFragment();let pos=0;pattern.lastIndex=0;for(const m of text.matchAll(pattern)){if(m.index>pos)frag.append(document.createTextNode(text.slice(pos,m.index)));const key=entries.find(e=>e[0].toLowerCase()===m[0].toLowerCase())?.[0];if(!key)continue;const b=document.createElement('button');b.type='button';b.className='glossary-term';b.textContent=m[0];b.setAttribute('aria-label',m[0]+'：點擊查看圖解');b.dataset.glossary=key;frag.append(b);pos=m.index+m[0].length;}frag.append(document.createTextNode(text.slice(pos)));node.replaceWith(frag);}}
document.addEventListener('click',e=>{const btn=e.target.closest?.('button[data-glossary]');if(btn)show(btn.dataset.glossary,btn)});
let pending=false;const observer=new MutationObserver(mutations=>{if(pending)return;const relevant=mutations.some(m=>Array.from(m.addedNodes).some(n=>n.nodeType===1&&!n.closest?.('.glossary-modal')&&!n.closest?.('.glossary-term')));if(!relevant)return;pending=true;queueMicrotask(()=>{pending=false;annotate(document.querySelector('main')||document.body)})});
function init(){annotate(document.querySelector('main')||document.body);observer.observe(document.querySelector('main')||document.body,{childList:true,subtree:true})}
if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',init);else init();
})();
