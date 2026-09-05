const integralPlaceholders = [
  "∫",
  "∬",
  "∭",
  "⨌",
  "∮",
  // "∯",
  // "∰",
  // "∱",
  // "∲",
  // "∳",
  // "⨑",
  // "⨒",
  // "⨓",
  // "⨔",
  // "⨕",
  // "⨖",
  // "⨋",
  // "⨍",
  // "⨎",
  // "⨏",
  // "⨗",
  // "⨘",
  // "⨙",
  // "⨚",
  // "⨛",
  // "⨜",
];

window.SomervilleSnippets = [
  {
    title: String.raw`Latin Alphabets`,
    comment: String.raw``,
    tex: String.raw`
$$\mathrm{ABCDEFGHIJKLMNOPQRSTUVWXYZ}$$
$$\mathrm{abcdefghijklmnopqrstuvwxyz}$$
$$ABCDEFGHIJKLMNOPQRSTUVWXYZ$$
$$abcdefghijklmnopqrstuvwxyz$$
$$\mathbf{ABCDEFGHIJKLMNOPQRSTUVWXYZ}$$
$$\mathbf{abcdefghijklmnopqrstuvwxyz}$$
$$\boldsymbol{ABCDEFGHIJKLMNOPQRSTUVWXYZ}$$
$$\boldsymbol{abcdefghijklmnopqrstuvwxyz}$$
$$0123456789$$
$$\mathbf{0123456789}$$
    `,
    placeholders: [],
  },
  {
    title: String.raw`Latin Alphabet Superscripts`,
    comment: String.raw``,
    tex: String.raw`
$$\mathrm{2^{ABCDEFGHIJKLMNOPQRSTUVWXYZ}}$$
$$\mathrm{2^{abcdefghijklmnopqrstuvwxyz}}$$
$$2^{ABCDEFGHIJKLMNOPQRSTUVWXYZ}$$
$$2^{abcdefghijklmnopqrstuvwxyz}$$
$$2^{\mathbf{ABCDEFGHIJKLMNOPQRSTUVWXYZ}}$$
$$2^{\mathbf{abcdefghijklmnopqrstuvwxyz}}$$
$$2^{\boldsymbol{ABCDEFGHIJKLMNOPQRSTUVWXYZ}}$$
$$2^{\boldsymbol{abcdefghijklmnopqrstuvwxyz}}$$
$$2^{0123456789}$$
$$2^{\mathbf{0123456789}}$$
    `,
    placeholders: [],
  },
  {
    title: String.raw`Greek Alphabet`,
    comment: String.raw``,
    tex: String.raw`
$$\mathrm{ΑΒΓΔΕΖΗΘΙΚΛΜΝΞΟΠΡΣΤΥΦΧΨΩ}$$
$$\mathrm{αβγδεζηθικλμνξοπρστυφχψω}$$
$$\mathit{ΑΒΓΔΕΖΗΘΙΚΛΜΝΞΟΠΡΣΤΥΦΧΨΩ}$$
$$\mathit{αβγδεζηθικλμνξοπρστυφχψω}$$
$$\mathbf{ΑΒΓΔΕΖΗΘΙΚΛΜΝΞΟΠΡΣΤΥΦΧΨΩ}$$
$$\mathbf{αβγδεζηθικλμνξοπρστυφχψω}$$
$$𝜜𝜝𝜞𝜟𝜠𝜡𝜢𝜣𝜤𝜥𝜦𝜧𝜨𝜩𝜪𝜫𝜬𝜮𝜯𝜰𝜱𝜲𝜳𝜴$$
$$𝜶𝜷𝜸𝜹𝜺𝜻𝜼𝜽𝜾𝜿𝝀𝝁𝝂𝝃𝝄𝝅𝝆𝝈𝝉𝝊𝝋𝝌𝝍𝝎$$
    `,
    placeholders: [],
  },
  {
    title: String.raw`Fraktur, Script, and Double-Struck`,
    comment: String.raw``,
    tex: String.raw`
$$\mathfrak{ABCDEFGHIJKLMNOPQRSTUVWXYZ}$$
$$\mathfrak{abcdefghijklmnopqrstuvwxyz}$$
$$𝕬𝕭𝕮𝕯𝕰𝕱𝕲𝕳𝕴𝕵𝕶𝕷𝕸𝕹𝕺𝕻𝕼𝕽𝕾𝕿𝖀𝖁𝖂𝖃𝖄𝖅$$
$$𝖆𝖇𝖈𝖉𝖊𝖋𝖌𝖍𝖎𝖏𝖐𝖑𝖒𝖓𝖔𝖕𝖖𝖗𝖘𝖙𝖚𝖛𝖜𝖝𝖞𝖟$$
$$\mathcal{ABCDEFGHIJKLMNOPQRSTUVWXYZ}$$
$$\mathcal{abcdefghijklmnopqrstuvwxyz}$$
$$𝓐𝓑𝓒𝓓𝓔𝓕𝓖𝓗𝓘𝓙𝓚𝓛𝓜𝓝𝓞𝓟𝓠𝓡𝓢𝓣𝓤𝓥𝓦𝓧𝓨𝓩$$
$$𝓪𝓫𝓬𝓭𝓮𝓯𝓰𝓱𝓲𝓳𝓴𝓵𝓶𝓷𝓸𝓹𝓺𝓻𝓼𝓽𝓾𝓿𝔀𝔁𝔂𝔃$$
$$\mathbb{ABCDEFGHIJKLMNOPQRSTUVWXYZ}$$
$$\mathbb{abcdefghijklmnopqrstuvwxyz}$$
$$\mathbb{0123456789}$$
    `,
    placeholders: [],
  },
    {
    title: String.raw`individual big operators`,
    comment: String.raw``,
    stretchy: true,
    tex: String.raw`
$$\ph\frac{\ph_{i=0}^n \frac{\ph_{j=0}^m a_n}{\ph_{j=0}^m b_n}}{\ph_{i=0}^n \frac{\ph_{j=0}^m a_n}{\ph_{j=0}^m u_n}}$$
    `,
    placeholders: ["\\sum","\\bigoplus","\\bigotimes","\\bigodot","\\prod","\\coprod"],
  },

      {
    title: String.raw`big operators`,
    comment: String.raw``,
    stretchy: true,
    tex: String.raw`
$$\sum\frac{\prod_{i=0}^n \frac{\coprod_{j=0}^m a_n}{\ph_{j=0}^m b_n}}{\ph_{i=0}^n \frac{\bigotimes_{j=0}^m a_n}{\bigodot_{j=0}^m u_n}}\qquad\bigoplus\frac{\bigodot_{i=0}^n \frac{\sum_{j=0}^m a_n}{\bigotimes_{j=0}^m b_n}}{\coprod_{i=0}^n \frac{\ph_{j=0}^m a_n}{\prod_{j=0}^m u_n}}$$

$$\bigotimes\frac{\ph_{i=0}^n \frac{\prod_{j=0}^m a_n}{\bigodot_{j=0}^m b_n}}{\coprod_{i=0}^n \frac{\sum_{j=0}^m a_n}{\bigoplus_{j=0}^m u_n}}\qquad\prod\frac{\bigoplus_{i=0}^n \frac{\bigodot_{j=0}^m a_n}{\sum_{j=0}^m b_n}}{\bigotimes_{i=0}^n \frac{\coprod_{j=0}^m a_n}{\ph_{j=0}^m u_n}}$$

$$\bigodot\frac{\coprod_{i=0}^n \frac{\bigoplus_{j=0}^m a_n}{\bigotimes_{j=0}^m b_n}}{\ph_{i=0}^n \frac{\prod_{j=0}^m a_n}{\sum_{j=0}^m u_n}}\qquad\ph\frac{\sum_{i=0}^n \frac{\bigotimes_{j=0}^m a_n}{\coprod_{j=0}^m b_n}}{\bigodot_{i=0}^n \frac{\bigoplus_{j=0}^m a_n}{\prod_{j=0}^m u_n}}$$

$$\prod\frac{\bigodot_{i=0}^n \frac{\ph_{j=0}^m a_n}{\coprod_{j=0}^m b_n}}{\sum_{i=0}^n \frac{\bigoplus_{j=0}^m a_n}{\bigotimes_{j=0}^m u_n}}\qquad\coprod\frac{\bigotimes_{i=0}^n \frac{\prod_{j=0}^m a_n}{\bigoplus_{j=0}^m b_n}}{\bigodot_{i=0}^n \frac{\sum_{j=0}^m a_n}{\ph_{j=0}^m u_n}}$$

$$\ph\frac{\bigoplus_{i=0}^n \frac{\sum_{j=0}^m a_n}{\prod_{j=0}^m b_n}}{\bigotimes_{i=0}^n \frac{\bigodot_{j=0}^m a_n}{\ph_{j=0}^m u_n}}\qquad\bigodot\frac{\prod_{i=0}^n \frac{\bigotimes_{j=0}^m a_n}{\ph_{j=0}^m b_n}}{\bigoplus_{i=0}^n \frac{\sum_{j=0}^m a_n}{\coprod_{j=0}^m u_n}}$$
    `,
    placeholders: ["\\sum","\\bigoplus","\\bigotimes","\\bigodot","\\prod","\\coprod"],
  },
  {
    title: String.raw`radicals`,
    comment: String.raw`Not expected to work well as variable math fonts are not supported`,
    tex: String.raw`
    $$\sqrt{\frac{1}{\sqrt{\frac{1}{\sqrt{2}}}}}$$
    `,
    placeholders: [],
  },
  {
    title: String.raw`Fences at All Sizes`,
    comment: String.raw`Firefox is doing something strange here; I do not think this is a font bug but will go back to see if I can stop this from happening`,
    tex: String.raw`
$$
(x)\qquad
\bigl(x\bigr)\qquad
\Bigl(x\Bigr)\qquad
\biggl(x\biggr)\qquad
\Biggl(x\Biggr)
$$

$$
\{x\}\qquad
\bigl\{x\bigr\}\qquad
\Bigl\{x\Bigr\}\qquad
\biggl\{x\biggr\}\qquad
\Biggl\{x\Biggr\}
$$

$$
[x]\qquad
\bigl[x\bigr]\qquad
\Bigl[x\Bigr]\qquad
\biggl[x\biggr]\qquad
\Biggl[x\Biggr]
$$

$$
\lceil x\rceil\qquad
\bigl\lceil x\bigr\rceil\qquad
\Bigl\lceil x\Bigr\rceil\qquad
\biggl\lceil x\biggr\rceil\qquad
\Biggl\lceil x\Biggr\rceil
$$

$$
\lfloor x\rfloor\qquad
\bigl\lfloor x\bigr\rfloor\qquad
\Bigl\lfloor x\Bigr\rfloor\qquad
\biggl\lfloor x\biggr\rfloor\qquad
\Biggl\lfloor x\Biggr\rfloor
$$

$$
\lvert x\rvert\qquad
\bigl\lvert x \bigr\rvert\qquad
\Bigl\lvert x \Bigr\rvert\qquad
\biggl\lvert x \biggr\rvert\qquad
\Biggl\lvert x \Biggr\rvert
$$

$$
\lVert x\rVert\qquad
\bigl\lVert x\bigr\rVert\qquad
\Bigl\lVert x\Bigr\rVert\qquad
\biggl\lVert x\biggr\rVert\qquad
\Biggl\lVert x\Biggr\rVert
$$


$$
⦀x⦀
$$
    `,
    placeholders: [],
    stretchy: true,
  },
  {
    title: String.raw`Integrals in context`,
    comment: String.raw``,
    tex: String.raw`

 
    Cauchy's Theorem is an important result in complex analysis.  It states that if $f$ is holomorphic on a simply connected domain $D$ and $C$ is a simple closed curve inside $D$ then $\ph_C f(z) dz=0$.
    
    
    From this we can easily prove Cauchy's integral formula.  Suppose $D$ and $C$ are as above and $w$ is a point inside $C$.  Suppose moreover that $C$ is parameterized counterclockwise.  Then it holds that
    
$$\ph_C \frac{f(z)}{w-z} dz = f(x)$$
    `,
    placeholders: integralPlaceholders,
  },
  {
    title: String.raw`Individual integrals`,
    comment: String.raw``,
    tex: String.raw`
$\ph f(x)dx$  $\ph\rule{0.001em}{0.5em}f(x)dx$ $\ph\rule{0.001em}{1em}f(x)dx$ $\ph\rule{0.001em}{1.5em}f(x)dx$ $\ph\rule{0.001em}{2em}f(x)dx$

$\ph_0^1 f(x)dx$  $\ph_0^1\rule{0.001em}{0.5em}f(x)dx$ $\ph_0^1\rule{0.001em}{1em}f(x)dx$ $\ph_0^1\rule{0.001em}{1.5em}f(x)dx$ $\ph_0^1\rule{0.001em}{2em}f(x)dx$

    `,
    placeholders: integralPlaceholders,
  },
  {
    title: String.raw`All Integrals`,
    comment: String.raw`Test color and height`,
    //$$∫∬∭⨌ ∮∯∰∱∲∳⨑⨒⨓⨔⨕⨖ ⨋⨍⨎⨏⨗⨘⨙⨚⨛⨜\rule{0.001em}{\ph em} $$
    tex: String.raw`
    $$∫∬∭⨌ ∮\rule{0.001em}{\ph em} $$
    `,
    placeholders: ["0.5","1","1.5","2","2.5"],
  },  
  {
    title: String.raw`Individual Horizontal Arrows`,
    comment: String.raw``,
    tex: String.raw`
$$A\ph B$$

We say that $f(x_n)\ph -l$ as $n\ph +A$ and write this as $$\lim_{n\ph A} f(x_n)=l$$
    `,
    placeholders: ["→","←","↔","↚","↛","↮","⇷","⇸","⇹","⇺","⇻","↞","↠","↢","↣","⤙","⤚","⤖","⤔","⤕","⤗","⤘","⤀","⤁","↤","↦","⇤","⇥","⤅","⤆","⤇","⤂","⤃","⤄","↼","↽","⇀","⇁","⥒","⥓","⥖","⥗","⥚","⥛","⥞","⥟","⥊","⥋","⥎","⥐","⇒","⇐","⇔","⇍","⇎","⇏","⤛","⤜"],
  },
  {
    title: String.raw`Regular and Long Arrows`,
    comment: String.raw``,
    mathml: String.raw`
<mtable class="arrow-table">
  <mtr><mtd><mo>→</mo></mtd><mtd><mo>⟶</mo></mtd></mtr>
  <mtr><mtd><mo>←</mo></mtd><mtd><mo>⟵</mo></mtd></mtr>
  <mtr><mtd><mo>↔</mo></mtd><mtd><mo>⟷</mo></mtd></mtr>
  <mtr><mtd><mo>⇒</mo></mtd><mtd><mo>⟹</mo></mtd></mtr>
  <mtr><mtd><mo>⇐</mo></mtd><mtd><mo>⟸</mo></mtd></mtr>
  <mtr><mtd><mo>⇔</mo></mtd><mtd><mo>⟺</mo></mtd></mtr>
  <mtr><mtd><mo>↦</mo></mtd><mtd><mo>⟼</mo></mtd></mtr>
  <mtr><mtd><mo>↤</mo></mtd><mtd><mo>⟻</mo></mtd></mtr>
  <mtr><mtd><mo>⤇</mo></mtd><mtd><mo>⟾</mo></mtd></mtr>
  <mtr><mtd><mo>⤆</mo></mtd><mtd><mo>⟽</mo></mtd></mtr>
</mtable>
    `,
    placeholders: [],
    stretchy: false,
  },
  {
    title: String.raw`Regular Arrow`,
    comment: String.raw``,
    mathml: String.raw`
<mtable class="arrow-table">
  <mtr><mtd><mo>←</mo></mtd><mtd><mo>→</mo></mtd><mtd><mo>↔</mo></mtd><mtd><mo>↢</mo></mtd><mtd><mo>↣</mo></mtd><mtd><mo>⤔</mo></mtd><mtd><mo>⤕</mo></mtd><mtd><mo>⤙</mo></mtd><mtd><mo>⤚</mo></mtd><mtd><mo>⤛</mo></mtd></mtr>
  <mtr><mtd><mo>⤜</mo></mtd><mtd><mo>⬹</mo></mtd><mtd><mo>⬺</mo></mtd><mtd><mo>↞</mo></mtd><mtd><mo>↠</mo></mtd><mtd><mo>⤀</mo></mtd><mtd><mo>⤁</mo></mtd><mtd><mo>⤖</mo></mtd><mtd><mo>⤗</mo></mtd><mtd><mo>⤘</mo></mtd></mtr>
  <mtr><mtd><mo>⬴</mo></mtd><mtd><mo>⬽</mo></mtd><mtd><mo>⬻</mo></mtd><mtd><mo>⬵</mo></mtd><mtd><mo>↼</mo></mtd><mtd><mo>↽</mo></mtd><mtd><mo>⇀</mo></mtd><mtd><mo>⇁</mo></mtd><mtd><mo>⥊</mo></mtd><mtd><mo>⥋</mo></mtd></mtr>
  <mtr><mtd><mo>⥎</mo></mtd><mtd><mo>⥐</mo></mtd><mtd><mo>⥒</mo></mtd><mtd><mo>⥓</mo></mtd><mtd><mo>⥖</mo></mtd><mtd><mo>⥗</mo></mtd><mtd><mo>⇤</mo></mtd><mtd><mo>⇥</mo></mtd><mtd><mo>↤</mo></mtd><mtd><mo>↦</mo></mtd></mtr>
  <mtr><mtd><mo>⤅</mo></mtd><mtd><mo>⤆</mo></mtd><mtd><mo>⤇</mo></mtd><mtd><mo>⥚</mo></mtd><mtd><mo>⥛</mo></mtd><mtd><mo>⥞</mo></mtd><mtd><mo>⥟</mo></mtd><mtd><mo>↹</mo></mtd><mtd><mo>⇄</mo></mtd><mtd><mo>⇆</mo></mtd></mtr>
  <mtr><mtd><mo>⇇</mo></mtd><mtd><mo>⇉</mo></mtd><mtd><mo>⇋</mo></mtd><mtd><mo>⇌</mo></mtd><mtd><mo>⥢</mo></mtd><mtd><mo>⥤</mo></mtd><mtd><mo>⥦</mo></mtd><mtd><mo>⥧</mo></mtd><mtd><mo>⥨</mo></mtd><mtd><mo>⥩</mo></mtd></mtr>
  <mtr><mtd><mo>⥪</mo></mtd><mtd><mo>⥫</mo></mtd><mtd><mo>⥬</mo></mtd><mtd><mo>⥭</mo></mtd><mtd><mo>⇍</mo></mtd><mtd><mo>⇎</mo></mtd><mtd><mo>⇏</mo></mtd><mtd><mo>⇐</mo></mtd><mtd><mo>⇒</mo></mtd><mtd><mo>⇔</mo></mtd></mtr>
  <mtr><mtd><mo>⇺</mo></mtd><mtd><mo>⇻</mo></mtd><mtd><mo>⤂</mo></mtd><mtd><mo>⤃</mo></mtd><mtd><mo>⤄</mo></mtd><mtd><mo>↮</mo></mtd><mtd><mo>⇷</mo></mtd><mtd><mo>⇸</mo></mtd><mtd><mo>⇹</mo></mtd></mtr>
  <mtr><mtd><mo>↚</mo></mtd><mtd><mo>↛</mo></mtd></mtr>
</mtable>
    `,
    placeholders: [],
    stretchy: false,
  },
  {
    title: String.raw`Long Arrow`,
    comment: String.raw``,
    mathml: String.raw`
<mtable class="arrow-table">
  <mtr><mtd><mo>⟻</mo></mtd><mtd><mo>⟼</mo></mtd><mtd><mo>⟽</mo></mtd><mtd><mo>⟾</mo></mtd><mtd><mo>⟸</mo></mtd><mtd><mo>⟹</mo></mtd><mtd><mo>⟺</mo></mtd><mtd><mo>⟵</mo></mtd><mtd><mo>⟶</mo></mtd><mtd><mo>⟷</mo></mtd></mtr>
</mtable>
    `,
    placeholders: [],
    stretchy: false,
  },
  {
    title: String.raw`Double Arrows`,
    comment: String.raw``,
    mathml: String.raw`
<mtable class="arrow-table">
  <mtr><mtd><mo>⤆</mo></mtd><mtd><mo>⤇</mo></mtd><mtd><mo>⇍</mo></mtd><mtd><mo>⇎</mo></mtd><mtd><mo>⇏</mo></mtd><mtd><mo>⇐</mo></mtd><mtd><mo>⇒</mo></mtd><mtd><mo>⇔</mo></mtd><mtd><mo>⤂</mo></mtd><mtd><mo>⤃</mo></mtd></mtr>
  <mtr><mtd><mo>⤄</mo></mtd><mtd><mo>⟽</mo></mtd><mtd><mo>⟾</mo></mtd><mtd><mo>⟸</mo></mtd><mtd><mo>⟹</mo></mtd><mtd><mo>⟺</mo></mtd></mtr>
</mtable>
    `,
    placeholders: [],
    stretchy: false,
  },
  {
    title: String.raw`Stroke Arrows`,
    comment: String.raw``,
    mathml: String.raw`
<mtable class="arrow-table">
  <mtr><mtd><mo>⤔</mo></mtd><mtd><mo>⤕</mo></mtd><mtd><mo>⬹</mo></mtd><mtd><mo>⬺</mo></mtd><mtd><mo>⤀</mo></mtd><mtd><mo>⤁</mo></mtd><mtd><mo>⤗</mo></mtd><mtd><mo>⤘</mo></mtd><mtd><mo>⬴</mo></mtd><mtd><mo>⬽</mo></mtd></mtr>
  <mtr><mtd><mo>⬵</mo></mtd><mtd><mo>⇍</mo></mtd><mtd><mo>⇎</mo></mtd><mtd><mo>⇏</mo></mtd><mtd><mo>⇺</mo></mtd><mtd><mo>⇻</mo></mtd><mtd><mo>⤂</mo></mtd><mtd><mo>⤃</mo></mtd><mtd><mo>⤄</mo></mtd><mtd><mo>↮</mo></mtd></mtr>
  <mtr><mtd><mo>⇷</mo></mtd><mtd><mo>⇸</mo></mtd><mtd><mo>⇹</mo></mtd><mtd><mo>↚</mo></mtd><mtd><mo>↛</mo></mtd></mtr>
</mtable>
    `,
    placeholders: [],
    stretchy: false,
  },
  {
    title: String.raw`Dual Arrows`,
    comment: String.raw``,
    mathml: String.raw`
<mtable class="arrow-table">
  <mtr><mtd><mo>↹</mo></mtd><mtd><mo>⇄</mo></mtd><mtd><mo>⇆</mo></mtd><mtd><mo>⇇</mo></mtd><mtd><mo>⇉</mo></mtd><mtd><mo>⇋</mo></mtd><mtd><mo>⇌</mo></mtd><mtd><mo>⥢</mo></mtd><mtd><mo>⥤</mo></mtd><mtd><mo>⥦</mo></mtd></mtr>
  <mtr><mtd><mo>⥧</mo></mtd><mtd><mo>⥨</mo></mtd><mtd><mo>⥩</mo></mtd><mtd><mo>⥪</mo></mtd><mtd><mo>⥫</mo></mtd><mtd><mo>⥬</mo></mtd><mtd><mo>⥭</mo></mtd></mtr>
</mtable>
    `,
    placeholders: [],
    stretchy: false,
  },
  {
    title: String.raw`Harpoon Arrows`,
    comment: String.raw``,
    mathml: String.raw`
<mtable class="arrow-table">
  <mtr><mtd><mo>↼</mo></mtd><mtd><mo>↽</mo></mtd><mtd><mo>⇀</mo></mtd><mtd><mo>⇁</mo></mtd><mtd><mo>⥊</mo></mtd><mtd><mo>⥋</mo></mtd><mtd><mo>⥎</mo></mtd><mtd><mo>⥐</mo></mtd><mtd><mo>⥒</mo></mtd><mtd><mo>⥓</mo></mtd></mtr>
  <mtr><mtd><mo>⥖</mo></mtd><mtd><mo>⥗</mo></mtd><mtd><mo>⥚</mo></mtd><mtd><mo>⥛</mo></mtd><mtd><mo>⥞</mo></mtd><mtd><mo>⥟</mo></mtd><mtd><mo>⇋</mo></mtd><mtd><mo>⇌</mo></mtd><mtd><mo>⥢</mo></mtd><mtd><mo>⥤</mo></mtd></mtr>
  <mtr><mtd><mo>⥦</mo></mtd><mtd><mo>⥧</mo></mtd><mtd><mo>⥨</mo></mtd><mtd><mo>⥩</mo></mtd><mtd><mo>⥪</mo></mtd><mtd><mo>⥫</mo></mtd><mtd><mo>⥬</mo></mtd><mtd><mo>⥭</mo></mtd></mtr>
</mtable>
    `,
    placeholders: [],
    stretchy: false,
  },
  {
    title: String.raw`Double Headed Arrows`,
    comment: String.raw``,
    mathml: String.raw`
<mtable class="arrow-table">
  <mtr><mtd><mo>↞</mo></mtd><mtd><mo>↠</mo></mtd><mtd><mo>⤀</mo></mtd><mtd><mo>⤁</mo></mtd><mtd><mo>⤖</mo></mtd><mtd><mo>⤗</mo></mtd><mtd><mo>⤘</mo></mtd><mtd><mo>⬴</mo></mtd><mtd><mo>⬽</mo></mtd><mtd><mo>⬻</mo></mtd></mtr>
  <mtr><mtd><mo>⬵</mo></mtd><mtd><mo>⤅</mo></mtd></mtr>
</mtable>
    `,
    placeholders: [],
    stretchy: false,
  },
  {
    title: String.raw`Tail Arrows`,
    comment: String.raw``,
    mathml: String.raw`
<mtable class="arrow-table">
  <mtr><mtd><mo>↢</mo></mtd><mtd><mo>↣</mo></mtd><mtd><mo>⤔</mo></mtd><mtd><mo>⤕</mo></mtd><mtd><mo>⤙</mo></mtd><mtd><mo>⤚</mo></mtd><mtd><mo>⤛</mo></mtd><mtd><mo>⤜</mo></mtd><mtd><mo>⬹</mo></mtd><mtd><mo>⬺</mo></mtd></mtr>
  <mtr><mtd><mo>⤖</mo></mtd><mtd><mo>⤗</mo></mtd><mtd><mo>⤘</mo></mtd><mtd><mo>⬽</mo></mtd><mtd><mo>⬻</mo></mtd></mtr>
</mtable>
    `,
    placeholders: [],
    stretchy: false,
  },
  {
    tex: String.raw`
$$\ph^\ph + \ph_\ph^\ph+M^M + M_M^M + \ph^M + M_{\ph}$$
    `,
    placeholders: ["M", "N", "A", "B","C","D"],
  },
  {
    tex: String.raw`
$$\ph^{\ph^\ph}$$
    `,
    placeholders: ["M", "N", "p", "y"],
  },
  {
    tex: String.raw`
$$\lim_{\ph \to 0} f(\ph ) = 0$$
    `,
    placeholders: ["x", "y", "z"],
  },
  {
    tex: String.raw`
$$\ph^{\ph^\ph}$$
    `,
    placeholders: ["M", "N", "p"],
  },
  {
    tex: String.raw`
$$\frac{\ph^2 - t^2}{1 + y^2}$$
    `,
    placeholders: ["x", "y", "M"],
  },
  {
    tex: String.raw`
$$\sum_{n=1}^{\infty} \frac{\ph^n}{n}$$
    `,
    placeholders: ["x", "N", "p"],
  },
  {
    tex: String.raw`
$$c = \pm\sqrt{a^2 + \ph^2}$$
    `,
    placeholders: ["a", "b", "c", "d", "e"],
  },
];
