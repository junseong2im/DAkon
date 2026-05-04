/* ───────────────────────────────────────────
   Stock Search — Autocomplete Module
   종목 자동완성: 이름/코드/영문 모두 검색
   ─────────────────────────────────────────── */

const StockSearch = (() => {
  // ── 종목 데이터: [표시명, 코드, 검색키워드들] ──
  const STOCKS = [
    // ── KOSPI 대형주 ──
    ["삼성전자", "005930.KS", "삼성전자 samsung 005930"],
    ["삼성전자우", "005935.KS", "삼성전자우 005935"],
    ["SK하이닉스", "000660.KS", "하이닉스 skhynix 000660"],
    ["LG에너지솔루션", "373220.KS", "lg에너지 373220"],
    ["삼성바이오로직스", "207940.KS", "삼성바이오 207940"],
    ["현대자동차", "005380.KS", "현대차 현대 hyundai 005380"],
    ["기아", "000270.KS", "기아차 kia 000270"],
    ["셀트리온", "068270.KS", "celltrion 068270"],
    ["KB금융", "105560.KS", "kb 국민은행 105560"],
    ["신한지주", "055550.KS", "신한금융 신한은행 055550"],
    ["포스코홀딩스", "005490.KS", "포스코 posco 005490"],
    ["삼성SDI", "006400.KS", "삼성sdi 006400"],
    ["LG화학", "051910.KS", "lg화학 051910"],
    ["현대모비스", "012330.KS", "모비스 012330"],
    ["삼성물산", "028260.KS", "028260"],
    ["삼성생명", "032830.KS", "032830"],
    ["하나금융지주", "086790.KS", "하나금융 하나은행 086790"],
    ["LG전자", "066570.KS", "lg전자 066570"],
    ["삼성화재", "000810.KS", "000810"],
    ["메리츠금융지주", "138040.KS", "메리츠금융 138040"],
    ["한국전력", "015760.KS", "한전 015760"],
    ["SK이노베이션", "096770.KS", "sk이노 096770"],
    ["SK텔레콤", "017670.KS", "skt 017670"],
    ["KT", "030200.KS", "케이티 030200"],
    ["LG", "003550.KS", "003550"],
    ["SK", "034730.KS", "034730"],
    ["두산에너빌리티", "034020.KS", "두산에너 034020"],
    ["한화에어로스페이스", "012450.KS", "한화에어로 012450"],
    ["한화오션", "042660.KS", "042660"],
    ["한화시스템", "272210.KS", "272210"],
    ["한화솔루션", "009830.KS", "009830"],
    ["한화", "000880.KS", "000880"],
    ["HD현대중공업", "329180.KS", "현대중공업 329180"],
    ["HD한국조선해양", "009540.KS", "한국조선해양 009540"],
    ["크래프톤", "259960.KS", "krafton 259960"],
    ["한미반도체", "042700.KS", "한미반 042700"],
    ["에코프로비엠", "247540.KS", "에코프로bm 247540"],
    ["에코프로", "086520.KS", "086520"],
    ["포스코퓨처엠", "003670.KS", "003670"],
    ["카카오뱅크", "323410.KS", "카뱅 323410"],
    ["우리금융지주", "316140.KS", "우리금융 우리은행 316140"],
    ["SK스퀘어", "402340.KS", "402340"],
    ["현대건설", "000720.KS", "000720"],
    ["고려아연", "010130.KS", "010130"],
    ["삼성에스디에스", "018260.KS", "삼성sds 018260"],
    ["LG이노텍", "011070.KS", "011070"],
    ["LG디스플레이", "034220.KS", "lgd 034220"],
    ["CJ제일제당", "097950.KS", "cj 097950"],
    ["아모레퍼시픽", "090430.KS", "아모레 090430"],
    ["대한항공", "003490.KS", "003490"],
    ["롯데케미칼", "011170.KS", "011170"],
    ["S-Oil", "010950.KS", "에스오일 010950"],
    ["하이브", "352820.KS", "hybe 352820"],
    ["현대글로비스", "086280.KS", "글로비스 086280"],
    ["두산밥캣", "241560.KS", "241560"],
    ["SK바이오팜", "326030.KS", "326030"],
    ["코스모신소재", "005070.KS", "005070"],

    // ── KOSDAQ 주요 종목 ──
    ["카카오", "035720.KQ", "kakao 035720"],
    ["네이버", "035420.KS", "naver 035420"],
    ["엔씨소프트", "036570.KS", "엔씨 ncsoft 036570"],
    ["넷마블", "251270.KS", "netmarble 251270"],
    ["펄어비스", "263750.KS", "263750"],
    ["위메이드", "112040.KQ", "112040"],
    ["셀트리온헬스케어", "091990.KQ", "셀트리온헬스 091990"],
    ["에이치엘비", "028300.KQ", "hlb 028300"],
    ["알테오젠", "196170.KQ", "196170"],
    ["리가켐바이오", "141080.KQ", "141080"],
    ["레인보우로보틱스", "277810.KQ", "277810"],
    ["두산로보틱스", "454910.KQ", "454910"],
    ["CJ ENM", "035760.KS", "cjenm 035760"],
    ["카카오게임즈", "293490.KQ", "293490"],

    // ── 미국 주요 종목 ──
    ["Apple (애플)", "AAPL", "애플 apple aapl"],
    ["Tesla (테슬라)", "TSLA", "테슬라 tesla tsla"],
    ["NVIDIA (엔비디아)", "NVDA", "엔비디아 nvidia nvda"],
    ["Microsoft (마이크로소프트)", "MSFT", "마이크로소프트 microsoft msft"],
    ["Alphabet (구글)", "GOOGL", "구글 google 알파벳 googl"],
    ["Amazon (아마존)", "AMZN", "아마존 amazon amzn"],
    ["Meta (메타)", "META", "메타 페이스북 meta"],
    ["Netflix (넷플릭스)", "NFLX", "넷플릭스 netflix nflx"],
    ["AMD", "AMD", "amd"],
    ["Intel (인텔)", "INTC", "인텔 intel intc"],
    ["Broadcom (브로드컴)", "AVGO", "브로드컴 broadcom avgo"],
    ["Palantir (팔란티어)", "PLTR", "팔란티어 palantir pltr"],
    ["Coinbase (코인베이스)", "COIN", "코인베이스 coinbase coin"],
    ["Disney (디즈니)", "DIS", "디즈니 disney dis"],
    ["Nike (나이키)", "NKE", "나이키 nike nke"],
    ["Coca-Cola (코카콜라)", "KO", "코카콜라 ko"],
    ["JPMorgan (JP모건)", "JPM", "jp모건 jpmorgan jpm"],
    ["Goldman Sachs (골드만삭스)", "GS", "골드만삭스 goldman gs"],
    ["Walmart (월마트)", "WMT", "월마트 walmart wmt"],
    ["Visa (비자)", "V", "비자 visa"],
    ["Mastercard (마스터카드)", "MA", "마스터카드 mastercard ma"],
    ["Uber (우버)", "UBER", "우버 uber"],
    ["Airbnb (에어비앤비)", "ABNB", "에어비앤비 airbnb abnb"],
    ["Shopify (쇼피파이)", "SHOP", "쇼피파이 shopify shop"],
    ["Roblox (로블록스)", "RBLX", "로블록스 roblox rblx"],
    ["Spotify (스포티파이)", "SPOT", "스포티파이 spotify spot"],

    // ── 미국 ETF ──
    ["SPY (S&P 500)", "SPY", "spy s&p500 에스앤피"],
    ["QQQ (나스닥100)", "QQQ", "qqq 나스닥 나스닥etf"],
    ["DIA (다우존스)", "DIA", "dia 다우 다우etf"],
    ["ARKK (ARK Innovation)", "ARKK", "arkk 아크"],
    ["TQQQ (나스닥3배)", "TQQQ", "tqqq"],
    ["SOXL (반도체3배)", "SOXL", "soxl"],

    // ── 암호화폐 ──
    ["비트코인 (BTC)", "BTC/USDT", "비트코인 비트 btc bitcoin"],
    ["이더리움 (ETH)", "ETH/USDT", "이더리움 이더 eth ethereum"],
    ["리플 (XRP)", "XRP/USDT", "리플 xrp ripple"],
    ["솔라나 (SOL)", "SOL/USDT", "솔라나 sol solana"],
    ["도지코인 (DOGE)", "DOGE/USDT", "도지코인 도지 doge"],
    ["에이다 (ADA)", "ADA/USDT", "에이다 카르다노 ada cardano"],
    ["폴카닷 (DOT)", "DOT/USDT", "폴카닷 dot polkadot"],
    ["아발란체 (AVAX)", "AVAX/USDT", "아발란체 avax avalanche"],
    ["체인링크 (LINK)", "LINK/USDT", "체인링크 link chainlink"],
    ["수이 (SUI)", "SUI/USDT", "수이 sui"],
  ];

  let dropdownEl = null;
  let inputEl = null;
  let selectedIdx = -1;
  let matches = [];

  function init() {
    inputEl = document.getElementById("prompt-input");
    if (!inputEl) return;

    // 드롭다운 생성
    dropdownEl = document.createElement("div");
    dropdownEl.className = "autocomplete-dropdown";
    dropdownEl.id = "autocomplete-dropdown";
    inputEl.parentElement.appendChild(dropdownEl);

    // 이벤트 바인딩
    inputEl.addEventListener("input", onInput);
    inputEl.addEventListener("keydown", onKeydown);
    document.addEventListener("click", (e) => {
      if (!dropdownEl.contains(e.target) && e.target !== inputEl) hide();
    });
  }

  function search(query) {
    if (!query || query.length < 1) return [];
    const q = query.toLowerCase().trim();
    const results = [];

    for (const [name, code, keywords] of STOCKS) {
      const searchText = `${name.toLowerCase()} ${code.toLowerCase()} ${keywords}`;
      if (searchText.includes(q)) {
        // 이름이 검색어로 시작하면 우선순위 높임
        const priority = name.toLowerCase().startsWith(q) ? 0 : 1;
        results.push({ name, code, priority });
      }
    }

    results.sort((a, b) => a.priority - b.priority || a.name.localeCompare(b.name));
    return results.slice(0, 8); // 최대 8개
  }

  function onInput() {
    const val = inputEl.value;
    // 공백 이전의 첫 단어만 검색 대상
    const firstWord = val.split(/\s+/)[0];
    matches = search(firstWord);

    if (matches.length === 0 || val.includes(" ") && matches.length <= 1) {
      hide();
      return;
    }
    render(matches, firstWord);
  }

  function render(items, query) {
    selectedIdx = -1;
    const q = query.toLowerCase();
    dropdownEl.innerHTML = items.map((item, i) => {
      // 매칭 부분 하이라이트
      const nameHtml = highlightMatch(item.name, q);
      const codeHtml = `<span class="ac-code">${item.code}</span>`;
      return `<div class="ac-item" data-idx="${i}">${nameHtml} ${codeHtml}</div>`;
    }).join("");

    // 클릭 이벤트
    dropdownEl.querySelectorAll(".ac-item").forEach(el => {
      el.addEventListener("mousedown", (e) => {
        e.preventDefault();
        selectItem(parseInt(el.dataset.idx));
      });
    });

    dropdownEl.classList.add("visible");
  }

  function highlightMatch(text, query) {
    const idx = text.toLowerCase().indexOf(query);
    if (idx === -1) return text;
    const before = text.slice(0, idx);
    const match = text.slice(idx, idx + query.length);
    const after = text.slice(idx + query.length);
    return `${before}<mark>${match}</mark>${after}`;
  }

  function selectItem(idx) {
    if (idx < 0 || idx >= matches.length) return;
    const item = matches[idx];
    // 첫 단어를 선택한 종목명으로 교체, 나머지 유지
    const parts = inputEl.value.split(/\s+/);
    parts[0] = item.name.replace(/\s*\(.*\)/, ""); // 괄호 제거
    inputEl.value = parts.join(" ");
    inputEl.focus();
    hide();
  }

  function onKeydown(e) {
    if (!dropdownEl.classList.contains("visible")) return;

    if (e.key === "ArrowDown") {
      e.preventDefault();
      selectedIdx = Math.min(selectedIdx + 1, matches.length - 1);
      updateSelection();
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      selectedIdx = Math.max(selectedIdx - 1, 0);
      updateSelection();
    } else if (e.key === "Enter" && selectedIdx >= 0) {
      e.preventDefault();
      e.stopPropagation();
      selectItem(selectedIdx);
    } else if (e.key === "Escape") {
      hide();
    }
  }

  function updateSelection() {
    dropdownEl.querySelectorAll(".ac-item").forEach((el, i) => {
      el.classList.toggle("selected", i === selectedIdx);
      if (i === selectedIdx) el.scrollIntoView({ block: "nearest" });
    });
  }

  function hide() {
    if (dropdownEl) {
      dropdownEl.classList.remove("visible");
      dropdownEl.innerHTML = "";
    }
    selectedIdx = -1;
    matches = [];
  }

  return { init };
})();

document.addEventListener("DOMContentLoaded", () => StockSearch.init());
