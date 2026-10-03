import type { GitGraph } from '../types'
import { PALETTE } from './layout'

const STYLE = String.raw`
:root{color-scheme:dark;--bg:#1c1c1e;--side:#232326;--fg:#e5e7eb;--dim:#9ca3af;--line:#33333a;--hover:#ffffff0d;--sel:#3b82f633;--menu:#2a2a2e;--bar:#141416;--on:#ffffff1c;--edge:#46464e}
:root[data-theme="light"]{color-scheme:light;--bg:#ffffff;--side:#f6f6f7;--fg:#1f2937;--dim:#6b7280;--line:#e5e7eb;--hover:#0000000a;--sel:#3b82f626;--menu:#ffffff;--bar:#ebebee;--on:#00000014;--edge:#c3c7ce}
*{box-sizing:border-box;margin:0;padding:0}
html,body{height:100%;background:var(--bg);color:var(--fg);font:13px/1.25 ui-sans-serif,system-ui,-apple-system,sans-serif}
body{display:flex;flex-direction:column;height:100vh}
.app{display:flex;flex:1;min-height:0}
nav{width:var(--nav-w,260px);flex:none;overflow:auto;background:var(--side);border-right:1px solid var(--line);padding:6px 6px 24px;white-space:nowrap;user-select:none}
nav summary,nav .leaf{display:block;padding:3px 8px;border-radius:6px;overflow:hidden;text-overflow:ellipsis;cursor:pointer}
nav summary:hover,nav .leaf:hover{background:var(--hover)}
nav summary{list-style:none}nav summary::-webkit-details-marker{display:none}
nav summary::before{content:'\25B8';display:inline-block;width:14px;font-size:10px;color:var(--dim)}
nav details[open]>summary::before{content:'\25BE'}
nav .kids{padding-left:12px}
nav>details>summary{font-size:11px;letter-spacing:.06em;text-transform:uppercase;color:var(--dim);margin-top:10px}
nav .leaf i{display:inline-block;width:8px;height:8px;border-radius:50%;margin-right:8px;vertical-align:1px}
nav .leaf.head{font-weight:700}
nav .leaf.on{background:var(--sel)}
#list .r.dim{opacity:.35}
#list svg .dim{opacity:.2}
nav .empty{padding:3px 22px;color:var(--dim)}
.main{flex:1;display:flex;flex-direction:column;min-width:0}
header{display:flex;align-items:center;gap:14px;padding:10px 16px;border-bottom:1px solid var(--line);background:var(--bar)}
header strong{font-size:14px}header span{color:var(--dim)}
header .find{margin-left:auto;display:flex;align-items:center;gap:8px;flex:none}
header .box{position:relative}
header .modes{display:flex;height:30px;border:1px solid var(--edge);border-radius:4px;overflow:hidden;background:var(--bg)}
header .modes button{height:100%;font:12px ui-sans-serif,system-ui,sans-serif;color:var(--dim);background:transparent;border:0;padding:0 12px;cursor:pointer}
header .modes button+button{border-left:1px solid var(--edge)}
header .modes button:hover{color:var(--fg);background:var(--hover)}
header .modes button.on{background:var(--on);color:var(--fg);font-weight:600}
header .modes button:disabled{opacity:.4;cursor:default}
#flist{flex:1;overflow:auto;padding:10px 0 14px}
#flist[hidden]{display:none}
.r.fr{position:static;padding-left:16px}
.fr .dot{width:9px;height:9px;border-radius:50%;flex:none}
.fr .paths{flex:0 1 auto;max-width:42%;min-width:0;overflow:hidden;text-overflow:ellipsis;color:var(--dim);font:11.5px ui-monospace,SFMono-Regular,Menlo,monospace}
#flist .none{padding:16px;color:var(--dim)}
header input{width:320px;height:30px;padding:0 10px;border-radius:4px;border:1px solid var(--edge);background:var(--bg);color:var(--fg);font:inherit}
header input.has{padding-right:84px}
header .count{position:absolute;right:9px;top:50%;transform:translateY(-50%);color:var(--dim);font-size:12px;pointer-events:none}
header{flex:none}
header .mode{width:30px;height:30px;display:grid;place-items:center;border:1px solid var(--edge);border-radius:4px;background:var(--bg);color:var(--dim);cursor:pointer;flex:none}
header .mode:hover{color:var(--fg);background:var(--hover)}
header .mode svg{width:16px;height:16px;fill:none;stroke:currentColor;stroke-width:1.8;stroke-linecap:round;stroke-linejoin:round}
header .mode .moon,:root[data-theme="light"] header .mode .sun{display:none}
:root[data-theme="light"] header .mode .moon{display:block}
#list{flex:1;overflow:auto;position:relative;padding:10px 0 14px}
#list svg{position:absolute;left:0;pointer-events:none}
path{fill:none;stroke-width:2;stroke-linecap:round}
.r{height:28px;display:flex;align-items:center;gap:14px;padding-right:16px;white-space:nowrap;position:absolute;left:0;right:0}
.r:hover{background:var(--hover)}.r.sel{background:var(--sel)}.r.head .s{font-weight:700}
.r .s{flex:1;min-width:0;overflow:hidden;text-overflow:ellipsis}
.r .p{font-size:11px;font-weight:600;padding:1px 8px;border-radius:10px;border:1px solid currentColor;flex:none}
.r .p.remote{opacity:.75}
.r .a{width:160px;flex:none;overflow:hidden;text-overflow:ellipsis;font-weight:600}
.r .d{width:130px;flex:none;color:var(--dim)}
.r .h{width:70px;flex:none;font:12px ui-monospace,SFMono-Regular,Menlo,monospace;color:var(--dim);cursor:copy}
.r .h:hover{color:var(--fg)}
#menu{position:fixed;z-index:10;min-width:200px;background:var(--menu);border:1px solid var(--line);border-radius:8px;padding:4px;box-shadow:0 8px 24px #0004}
#menu div{padding:6px 10px;border-radius:5px;cursor:pointer;white-space:nowrap}
#menu div:hover{background:var(--sel)}
#menu small{display:block;color:var(--dim);padding:4px 10px 2px;max-width:340px;overflow:hidden;text-overflow:ellipsis}
.grip{flex:none;background:transparent;position:relative;z-index:2}
.grip:hover,.grip.on{background:#3b82f666}
.grip.v{width:5px;margin:0 -2px;cursor:col-resize}
.grip.h{height:6px;cursor:row-resize;position:absolute;left:0;right:0;top:-3px}
#detail{flex:none;height:var(--detail-h,260px);display:flex;flex-direction:column;border-top:1px solid var(--line);background:var(--side);position:relative;min-height:0}
#detail[hidden]{display:none}
#detail .head{flex:none;display:flex;align-items:center;gap:10px;padding:10px 16px;background:var(--bar);border-bottom:1px solid var(--line);white-space:nowrap;min-width:0}
#detail .head .dot{width:9px;height:9px;border-radius:50%;flex:none}
#detail .head .sha{font:12px ui-monospace,SFMono-Regular,Menlo,monospace;padding:2px 7px;border-radius:4px;background:var(--hover);cursor:copy;flex:none}
#detail .head .sha:hover{color:var(--fg);background:var(--sel)}
#detail .head .who{color:var(--dim);overflow:hidden;text-overflow:ellipsis;min-width:0}
#detail .actions{margin-left:auto;display:flex;align-items:center;gap:6px;flex:none}
#detail .seg[hidden]{display:none}
#detail .seg{display:flex;height:30px;border:1px solid var(--edge);border-radius:4px;overflow:hidden;background:var(--bg)}
#detail .seg button{display:flex;align-items:center;gap:6px;font:12px ui-sans-serif,system-ui,sans-serif;color:var(--fg);background:transparent;border:0;height:100%;padding:0 12px;cursor:pointer}
#detail .seg button+button{border-left:1px solid var(--edge)}
#detail .seg button:hover{background:var(--hover)}
#detail .seg button.done{color:#22c55e}
#detail .seg svg{width:14px;height:14px;fill:none;stroke:currentColor;stroke-width:1.8;stroke-linecap:round;stroke-linejoin:round;opacity:.85}
#detail .x{width:30px;height:30px;display:grid;place-items:center;border:1px solid var(--edge);border-radius:4px;background:var(--bg);color:var(--dim);font-size:16px;line-height:1;cursor:pointer;margin-left:2px}
#detail .x:hover{background:var(--hover);color:var(--fg)}
#detail .tabs{display:flex;height:30px;margin-left:14px;border:1px solid var(--edge);border-radius:4px;overflow:hidden;background:var(--bg);flex:none}
#detail .tabs button{height:100%;font:12px ui-sans-serif,system-ui,sans-serif;color:var(--dim);background:transparent;border:0;padding:0 12px;cursor:pointer;display:flex;align-items:center;gap:6px}
#detail .tabs button+button{border-left:1px solid var(--edge)}
#detail .tabs button:hover{color:var(--fg);background:var(--hover)}
#detail .tabs button.on{background:var(--on);color:var(--fg);font-weight:600}
#detail .tabs .n{font-size:11px;font-weight:400;color:var(--dim);background:var(--hover);border-radius:8px;padding:0 6px}
#detail .changes{flex:1;display:flex;min-height:0}
#detail .changes[hidden],#detail .cols[hidden]{display:none}
#detail .files{width:var(--files-w,340px);flex:none;overflow:auto;padding:6px}
#detail .file{display:flex;align-items:center;gap:8px;padding:4px 8px;border-radius:6px;cursor:pointer;white-space:nowrap}
#detail .file:hover{background:var(--hover)}#detail .file.on{background:var(--sel)}
#detail .st{flex:none;width:18px;height:18px;border-radius:4px;display:grid;place-items:center;font:700 10px ui-monospace,Menlo,monospace;color:#fff}
#detail .st.A{background:#16a34a}#detail .st.M{background:#d97706}#detail .st.D{background:#dc2626}#detail .st.R,#detail .st.C{background:#2563eb}#detail .st.T,#detail .st.U,#detail .st.X{background:#6b7280}
#detail .fp{flex:1;min-width:0;overflow:hidden;text-overflow:ellipsis}
#detail .fp .dir{color:var(--dim);margin-left:6px;font-size:12px}
#detail .num{flex:none;font:11.5px ui-monospace,Menlo,monospace}
#detail .num .add,#detail .num .del{margin-left:6px}
#detail .note{padding:6px 10px 8px;color:var(--dim);font-size:12px}
#detail .diff{flex:1;overflow:auto;border-left:1px solid var(--line);min-width:0;background:var(--bg)}
#detail .dh{position:sticky;top:0;z-index:1;display:flex;align-items:center;gap:8px;padding:7px 12px;background:var(--side);border-bottom:1px solid var(--line);font-weight:600;white-space:nowrap}
#detail .dh .num{margin-left:auto;font-weight:400}
#detail .hunks{padding:12px 12px 4px}
#detail .hunk{border:1px solid var(--line);border-radius:8px;overflow:hidden;margin-bottom:12px;background:var(--bg)}
#detail .hh{display:flex;align-items:center;gap:10px;padding:6px 12px;background:var(--side);border-bottom:1px solid var(--line);color:var(--dim);font-size:12px;white-space:nowrap}
#detail .hh b{color:var(--fg);font-weight:600}
#detail .hh .ctx{min-width:0;overflow:hidden;text-overflow:ellipsis;font:11.5px ui-monospace,SFMono-Regular,Menlo,monospace;color:var(--dim);padding-left:10px;border-left:1px solid var(--line)}
#detail .hunk .body{overflow-x:auto;padding:4px 0}
#detail .lines{font:12px/19px ui-monospace,SFMono-Regular,Menlo,monospace;min-width:max-content}
#detail .l{display:grid;grid-template-columns:44px 44px 1fr}
#detail .l span{color:var(--dim);text-align:right;padding-right:10px;user-select:none;opacity:.7}
#detail .l code{white-space:pre;padding-right:16px;user-select:text;font:inherit}
#detail .l.a{background:#22c55e1f}#detail .l.a span{background:#22c55e14}#detail .l.a code{color:inherit}
#detail .l.d{background:#ef44441f}#detail .l.d span{background:#ef444414}
#detail .l.n code{color:var(--dim);font-style:italic}
#detail .empty{padding:16px;color:var(--dim)}
#detail .cols{flex:1;display:flex;min-height:0}
#detail .meta{width:var(--meta-w,460px);flex:none;overflow:auto;padding:12px 14px 14px 16px;min-width:0}
#detail .text{flex:1;overflow:auto;padding:12px 18px 16px;border-left:1px solid var(--line);min-width:0}
#detail h2{font-size:14px;margin:0 0 10px;user-select:text}
#detail pre{white-space:pre-wrap;font:12.5px/1.5 ui-sans-serif,system-ui,sans-serif;user-select:text}
#detail .none{color:var(--dim)}
#detail dl{display:grid;grid-template-columns:auto minmax(0,1fr);gap:2px 14px}
#detail dt{color:var(--dim);white-space:nowrap}
#detail dd{user-select:text;min-width:0;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;line-height:20px;padding:2px 0}#detail dt{padding:2px 0;line-height:20px}
#detail code{font:12px ui-monospace,SFMono-Regular,Menlo,monospace}
#detail .link{cursor:pointer;text-decoration:underline;text-decoration-color:var(--line)}
#detail .add{color:#22c55e}#detail .del{color:#ef4444}
#detail .p{display:inline-block;vertical-align:middle;font-size:11px;line-height:15px;font-weight:600;padding:0 8px;border-radius:9px;border:1px solid currentColor;margin-right:6px}
#menu hr{border:0;border-top:1px solid var(--line);margin:4px 2px}
#toast{position:fixed;bottom:18px;left:50%;transform:translateX(-50%);background:var(--menu);border:1px solid var(--line);padding:7px 14px;border-radius:8px;box-shadow:0 6px 18px #0003}
`

// The page's own script: plain ES5-style JavaScript with no template literals, so it can
// sit inside this module's String.raw template untouched.
const SCRIPT = String.raw`
(function () {
  var ROW = 28, LANE = 14, GUTTER = 14, CHUNK = 400;
  var commits = DATA.commits, edges = DATA.edges;
  var list = document.getElementById('list');
  var flist = document.getElementById('flist');
  var preferred = null;
  var menu = document.getElementById('menu');
  var toast = document.getElementById('toast');

  function esc(text) {
    return String(text).replace(/[&<>"]/g, function (c) { return '&#' + c.charCodeAt(0) + ';'; });
  }
  function colour(lane) { return PALETTE[lane % PALETTE.length]; }

  var used = {};
  commits.forEach(function (c) { used[c.lane] = true; });
  edges.forEach(function (e) { used[e.lane] = true; used[e.childLane] = true; if (e.parentRow >= 0) used[e.parentLane] = true; });
  var lanes = Object.keys(used).map(Number).sort(function (a, b) { return a - b; });
  var column = {};
  lanes.forEach(function (lane, index) { column[lane] = index; });
  function x(lane) { return GUTTER + column[lane] * LANE; }
  function y(row) { return row * ROW + ROW / 2; }
  var graphWidth = GUTTER * 2 + Math.max(lanes.length - 1, 0) * LANE;
  var total = commits.length * ROW;

  function when(time) {
    var now = Date.now(), date = new Date(time * 1000), minutes = Math.floor((now - date) / 60000);
    if (minutes < 1) return 'Just now';
    if (minutes < 60) return minutes + (minutes === 1 ? ' minute ago' : ' minutes ago');
    var pad = function (n) { return (n < 10 ? '0' : '') + n; };
    var clock = pad(date.getHours()) + ':' + pad(date.getMinutes());
    var today = new Date(); today.setHours(0, 0, 0, 0);
    var day = new Date(date); day.setHours(0, 0, 0, 0);
    var days = Math.round((today - day) / 86400000);
    if (days === 0) return 'Today ' + clock;
    if (days === 1) return 'Yesterday ' + clock;
    return pad(date.getDate()) + '/' + pad(date.getMonth() + 1) + '/' + date.getFullYear() + ', ' + clock;
  }

  function edgePath(e) {
    var runX = x(e.lane), childX = x(e.childLane), childY = y(e.childRow), half = ROW / 2;
    var off = e.parentRow < 0, parentX = off ? runX : x(e.parentLane), parentY = off ? total : y(e.parentRow);
    var d = 'M' + childX + ' ' + childY;
    if (childX !== runX && parentX !== runX && parentY - childY < ROW * 2) {
      var middle = (childY + parentY) / 2;
      return d + 'C' + childX + ' ' + middle + ' ' + parentX + ' ' + middle + ' ' + parentX + ' ' + parentY;
    }
    if (childX !== runX) d += 'C' + childX + ' ' + (childY + half) + ' ' + runX + ' ' + (childY + half) + ' ' + runX + ' ' + (childY + ROW);
    d += 'V' + (parentX !== runX ? parentY - ROW : parentY);
    if (parentX !== runX) d += 'C' + runX + ' ' + (parentY - half) + ' ' + parentX + ' ' + (parentY - half) + ' ' + parentX + ' ' + parentY;
    return d;
  }

  // The graph in chunks of rows, each its own SVG, so no single layer grows too tall.
  var svg = '';
  for (var start = 0; start < commits.length; start += CHUNK) {
    var end = Math.min(commits.length, start + CHUNK), top = start * ROW, height = (end - start) * ROW;
    var parts = [];
    edges.forEach(function (e) {
      var last = e.parentRow < 0 ? Infinity : e.parentRow;
      if (e.childRow < end && last >= start) parts.push('<path data-c="' + e.childRow + '" data-p="' + e.parentRow + '" stroke="' + colour(e.lane) + '" d="' + edgePath(e) + '"/>');
    });
    for (var row = start; row < end; row++) {
      var c = commits[row], cx = x(c.lane), cy = y(row);
      parts.push(c.isHead
        ? '<circle data-r="' + row + '" cx="' + cx + '" cy="' + cy + '" r="5.5" fill="var(--bg)" stroke="' + colour(c.lane) + '" stroke-width="2.5"/>'
        : '<circle data-r="' + row + '" cx="' + cx + '" cy="' + cy + '" r="4.5" fill="' + colour(c.lane) + '"/>');
    }
    svg += '<svg style="top:' + top + 'px" width="' + graphWidth + '" height="' + height + '" viewBox="0 ' + top + ' ' + graphWidth + ' ' + height + '">' + parts.join('') + '</svg>';
  }

  var rows = commits.map(function (c) {
    var pills = c.refs.map(function (r) {
      return '<span class="p ' + r.kind + '" style="color:' + colour(c.lane) + '">' + esc(r.kind === 'tag' ? '⌂ ' + r.label : r.label) + '</span>';
    }).join('');
    return '<div class="r' + (c.isHead ? ' head' : '') + '" data-row="' + c.row + '" style="top:' + c.row * ROW + 'px;padding-left:' + graphWidth + 'px">' +
      '<span class="s" title="' + esc(c.subject) + '">' + esc(c.subject) + '</span>' + pills +
      '<span class="a">' + esc(c.author) + (c.isCommittedByOther ? '*' : '') + '</span>' +
      '<span class="d">' + when(c.time) + '</span><span class="h" title="Click to copy">' + c.hash + '</span></div>';
  }).join('');
  list.innerHTML = '<div style="height:' + total + 'px;position:relative">' + svg + rows + '</div>';

  // ---------------------------------------------------------------- sidebar
  function tree(names) {
    var root = { kids: {} };
    names.forEach(function (entry) {
      var level = root, parts = entry.name.split('/');
      parts.forEach(function (part, index) {
        level.kids[part] = level.kids[part] || { kids: {} };
        if (index === parts.length - 1 && !level.kids[part].ref) level.kids[part].ref = entry;
        level = level.kids[part];
      });
    });
    return root;
  }
  function leaves(node) {
    var count = node.ref ? 1 : 0;
    Object.keys(node.kids).forEach(function (k) { count += leaves(node.kids[k]); });
    return count;
  }
  function holdsHead(node) {
    if (node.ref && node.ref.isHead) return true;
    return Object.keys(node.kids).some(function (k) { return holdsHead(node.kids[k]); });
  }
  function render(node, prefix, openAll) {
    return Object.keys(node.kids).sort(function (a, b) { return a.localeCompare(b); }).map(function (name) {
      var child = node.kids[name], html = '';
      if (child.ref) {
        html += '<div class="leaf' + (child.ref.isHead ? ' head' : '') + '" data-row="' + child.ref.row + '" data-name="' + esc(prefix + name) + '" title="' + esc(prefix + name) + '">' +
          '<i style="background:' + colour(child.ref.lane) + '"></i>' + esc(name) + '</div>';
      }
      if (Object.keys(child.kids).length) {
        var open = openAll || holdsHead(child) || leaves(child) <= 4;
        html += '<details' + (open ? ' open' : '') + '><summary>' + esc(name) + '</summary><div class="kids">' + render(child, prefix + name + '/', false) + '</div></details>';
      }
      return html;
    }).join('');
  }
  var sets = { branches: [], remotes: [], tags: [] }, seen = {};
  commits.forEach(function (c) {
    ['branches', 'remotes', 'tags'].forEach(function (kind) {
      c[kind].forEach(function (name) {
        var key = kind + ':' + name;
        if (seen[key]) return;
        seen[key] = true;
        sets[kind].push({ name: name, row: c.row, lane: c.lane, isHead: kind === 'branches' && name === c.headBranch });
      });
    });
  });
  function section(title, names, openAll) {
    var body = names.length ? render(tree(names), '', openAll) : '<div class="empty">None</div>';
    return '<details open><summary>' + title + '</summary><div class="kids">' + body + '</div></details>';
  }
  document.getElementById('refs').innerHTML =
    section('Branches', sets.branches, false) + section('Remotes', sets.remotes, true) + section('Tags', sets.tags, false);

  // --------------------------------------------------------------- behaviour
  var selected = null;
  function select(row) {
    if (selected) selected.classList.remove('sel');
    if (!flist.hidden) {
      selected = flist.querySelector('.r[data-row="' + row + '"]');
      if (selected) {
        selected.classList.add('sel');
        selected.scrollIntoView({ block: 'nearest' });
        return;
      }
      // A commit outside the file filter: leave the filter and show it in the full graph.
      clearFiles();
      find.value = '';
      setCount('');
    }
    selected = list.querySelector('.r[data-row="' + row + '"]');
    if (!selected) return;
    selected.classList.add('sel');
    var top = row * ROW + 10;
    if (top < list.scrollTop || top + ROW > list.scrollTop + list.clientHeight) {
      list.scrollTop = Math.max(0, top - list.clientHeight / 2 + ROW / 2);
    }
  }
  function show(text) {
    toast.textContent = text;
    toast.hidden = false;
    clearTimeout(show.timer);
    show.timer = setTimeout(function () { toast.hidden = true; }, 1400);
  }
  function copy(text, label) {
    var done = function () { show('Copied ' + (label || text)); };
    if (navigator.clipboard && navigator.clipboard.writeText) {
      navigator.clipboard.writeText(text).then(done, function () { fallback(text); done(); });
    } else { fallback(text); done(); }
  }
  function fallback(text) {
    var area = document.createElement('textarea');
    area.value = text; document.body.appendChild(area); area.select();
    document.execCommand('copy'); area.remove();
  }
  // Add to prompt: the page posts the text to the local bridge; the Claude Code session
  // that opened the page collects it and puts it in its prompt box (never sends it).
  function addToPrompt(text, label) {
    if (!BRIDGE) { copy(text, label); return; }
    fetch('/prompt', { method: 'POST', body: JSON.stringify({ session: BRIDGE.session, token: BRIDGE.token, text: text }) })
      .then(function (response) {
        show(response.ok ? 'Added ' + (label || text) + ' to the prompt' : 'Could not reach Claude Code: copied instead');
        if (!response.ok) copy(text, label);
      }, function () { copy(text, label); show('Could not reach Claude Code: copied instead'); });
  }
  function both(text, label, what) {
    var items = [['Copy ' + what, function () { copy(text, label); }]];
    if (BRIDGE) items.push(['Add ' + what + ' to prompt', function () { addToPrompt(text, label); }]);
    return items;
  }

  function openMenu(event, title, items) {
    event.preventDefault();
    menu.innerHTML = '<small>' + esc(title) + '</small>' + items.map(function (item, index) {
      return item ? '<div data-index="' + index + '">' + esc(item[0]) + '</div>' : '<hr>';
    }).join('');
    menu.hidden = false;
    var left = Math.min(event.clientX, innerWidth - menu.offsetWidth - 8);
    var top = Math.min(event.clientY, innerHeight - menu.offsetHeight - 8);
    menu.style.left = left + 'px'; menu.style.top = top + 'px';
    menu.onclick = function (e) {
      var index = e.target.getAttribute('data-index');
      if (index !== null) items[Number(index)][1]();
      menu.hidden = true;
    };
  }
  document.addEventListener('click', function (e) { if (!menu.contains(e.target)) menu.hidden = true; });
  document.addEventListener('keydown', function (e) { if (e.key === 'Escape') menu.hidden = true; });
  list.addEventListener('scroll', function () { menu.hidden = true; });

  // Focus: a branch, remote or tag picked in the sidebar keeps its history (every commit
  // reachable from it) at full strength in the graph and dims the rest. The same entry
  // again, or Escape, clears it.
  var parentsOf = {}, focusLeaf = null;
  edges.forEach(function (e) {
    if (e.parentRow >= 0) (parentsOf[e.childRow] = parentsOf[e.childRow] || []).push(e.parentRow);
  });
  function setFocus(leaf) {
    if (focusLeaf) focusLeaf.classList.remove('on');
    focusLeaf = leaf;
    var reach = null;
    if (leaf) {
      leaf.classList.add('on');
      reach = {};
      var stack = [Number(leaf.getAttribute('data-row'))];
      while (stack.length) {
        var row = stack.pop();
        if (reach[row]) continue;
        reach[row] = true;
        (parentsOf[row] || []).forEach(function (parent) { if (!reach[parent]) stack.push(parent); });
      }
    }
    list.querySelectorAll('.r').forEach(function (el) {
      el.classList.toggle('dim', !!reach && !reach[el.getAttribute('data-row')]);
    });
    list.querySelectorAll('circle').forEach(function (el) {
      el.classList.toggle('dim', !!reach && !reach[el.getAttribute('data-r')]);
    });
    list.querySelectorAll('path').forEach(function (el) {
      var child = el.getAttribute('data-c'), parent = el.getAttribute('data-p');
      el.classList.toggle('dim', !!reach && (!reach[child] || (parent !== '-1' && !reach[parent])));
    });
  }
  document.getElementById('refs').addEventListener('click', function (e) {
    var leaf = e.target.closest('.leaf');
    if (!leaf) return;
    setFocus(leaf === focusLeaf ? null : leaf);
    select(Number(leaf.getAttribute('data-row')));
  });
  document.addEventListener('keydown', function (e) {
    if (e.key === 'Escape' && focusLeaf && menu.hidden && detail.hidden && !(e.target.closest && e.target.closest('input'))) setFocus(null);
  });
  document.getElementById('refs').addEventListener('contextmenu', function (e) {
    var leaf = e.target.closest('.leaf');
    if (!leaf) return;
    var name = leaf.getAttribute('data-name'), c = commits[Number(leaf.getAttribute('data-row'))];
    openMenu(e, name, both(name, name, 'name').concat([null],
      both(c.hash, c.hash, 'latest commit hash'),
      [null, ['Go to latest commit', function () { select(c.row); }]]));
  });
  // Details: a click on a row opens everything about that commit below the list.
  var detail = document.getElementById('detail'), shownRow = -1;
  function stamp(time) {
    var date = new Date(time * 1000), pad = function (n) { return (n < 10 ? '0' : '') + n; };
    var full = pad(date.getDate()) + '/' + pad(date.getMonth() + 1) + '/' + date.getFullYear() + ', ' + pad(date.getHours()) + ':' + pad(date.getMinutes());
    var relative = when(time);
    return relative === full ? full : full + ' (' + relative + ')';
  }
  function person(name, email) { return esc(name) + ' &lt;' + esc(email) + '&gt;'; }
  function openDetail(c) {
    shownRow = c.row;
    var byRow = {};
    commits.forEach(function (other) { byRow[other.hash] = other.row; });
    var parents = c.parentHashes.map(function (hash) {
      return byRow[hash] === undefined ? '<code>' + hash + '</code>' : '<code class="link" data-go="' + byRow[hash] + '">' + hash + '</code>';
    }).join(', ') || 'none (first commit)';
    var refs = c.refs.map(function (r) {
      return '<span class="p" style="color:' + colour(c.lane) + '">' + esc(r.kind === 'tag' ? '⌂ ' + r.label : r.label) + '</span>';
    }).join('');
    var plain = function (html) { return html.replace(/<[^>]*>/g, '').replace(/&#(\d+);/g, function (match, code) { return String.fromCharCode(Number(code)); }).replace(/&lt;/g, '<').replace(/&gt;/g, '>').replace(/&amp;/g, '&'); };
    var rows = [
      ['Hash', '<code class="link" data-copy="' + c.fullHash + '">' + c.fullHash + '</code>'],
      ['Parents', parents],
      ['Author', person(c.author, c.authorEmail)],
      ['Authored', stamp(c.time)],
    ];
    if (c.committer !== c.author || c.committerEmail !== c.authorEmail) rows.push(['Committer', person(c.committer, c.committerEmail)]);
    if (c.commitTime !== c.time) rows.push(['Committed', stamp(c.commitTime)]);
    if (refs) rows.push(['Refs', refs]);
    if (c.parentHashes.length > 1 && !c.stats.files) rows.push(['Changes', 'merge commit (its changes are on the merged branch)']);
    else rows.push(['Changes', c.stats.files + (c.stats.files === 1 ? ' file' : ' files') + ', <span class="add">+' + c.stats.insertions + '</span> <span class="del">−' + c.stats.deletions + '</span>']);
    rows.forEach(function (r) { r.push(esc(plain(r[1]))); });
    var icon = {
      text: '<svg viewBox="0 0 24 24"><rect x="9" y="9" width="12" height="12" rx="2"/><path d="M5 15H4a1 1 0 0 1-1-1V4a1 1 0 0 1 1-1h10a1 1 0 0 1 1 1v1"/></svg>',
      markdown: '<svg viewBox="0 0 24 24"><rect x="2" y="5" width="20" height="14" rx="2"/><path d="M6 15V9l3 3 3-3v6M16 9v6m-2-2 2 2 2-2"/></svg>',
    };
    detail.innerHTML = '<div class="grip h" data-resize="detail"></div>' +
      '<div class="head"><span class="dot" style="background:' + colour(c.lane) + '"></span>' +
      '<code class="sha" data-copy="' + c.fullHash + '" title="Copy the full hash">' + c.hash + '</code>' +
      '<span class="who">' + esc(c.author) + ' · ' + when(c.time) + '</span>' +
      '<div class="tabs"><button data-tab="details"' + (tab === 'details' ? ' class="on"' : '') + '>Details</button>' +
      (BRIDGE ? '<button data-tab="changes"' + (tab === 'changes' ? ' class="on"' : '') + '>Changes <span class="n">' + (c.stats.files || '…') + '</span></button>' : '') + '</div>' +
      '<div class="actions"><div class="seg"' + (tab === 'changes' && BRIDGE ? ' hidden' : '') + '>' +
      '<button data-copy-as="text" title="Subject and description as plain text">' + icon.text + 'Copy text</button>' +
      '<button data-copy-as="markdown" title="Markdown in a code block: pastes into Slack as a code block, into an editor as Markdown">' + icon.markdown + 'Copy Markdown</button>' +
      '</div><button class="x" title="Close (Esc)">×</button></div></div>' +
      '<div class="cols"' + (tab === 'changes' && BRIDGE ? ' hidden' : '') + '><div class="meta"><dl>' + rows.map(function (r) { return '<dt>' + r[0] + '</dt><dd title="' + r[2] + '">' + r[1] + '</dd>'; }).join('') + '</dl></div>' +
      '<div class="grip v" data-resize="meta"></div>' +
      '<div class="text"><h2>' + esc(c.subject) + '</h2>' + (c.body ? '<pre>' + esc(c.body) + '</pre>' : '<p class="none">No further description.</p>') + '</div></div>' +
      '<div class="changes"' + (tab === 'changes' && BRIDGE ? '' : ' hidden') + '><div class="files"><p class="empty">Loading changes…</p></div>' +
      '<div class="grip v" data-resize="files"></div><div class="diff"></div></div>';
    detail.hidden = false;
    if (tab === 'changes' && BRIDGE) loadChanges(c);
  }
  function closeDetail() { detail.hidden = true; shownRow = -1; }

  // Changes: the commit's files and patches, fetched from the bridge when the tab opens
  // and kept for the page's life. A merge shows its changes against the first parent.
  var tab = 'details', changesOf = {}, shownFile = 0;
  function showTab(name) {
    tab = name;
    detail.querySelectorAll('.tabs button').forEach(function (b) { b.classList.toggle('on', b.getAttribute('data-tab') === name); });
    detail.querySelector('.cols').hidden = name !== 'details';
    detail.querySelector('.changes').hidden = name !== 'changes';
    // The copy buttons copy the message, so they belong to the Details tab alone.
    detail.querySelector('.seg').hidden = name !== 'details';
    if (name === 'changes' && shownRow >= 0) loadChanges(commits[shownRow]);
  }
  function loadChanges(c) {
    if (changesOf[c.fullHash]) return renderChanges(c, changesOf[c.fullHash]);
    fetch('/changes?repo=' + encodeURIComponent(BRIDGE.repo) + '&hash=' + c.fullHash)
      .then(function (response) { return response.json(); })
      .then(function (data) {
        if (data.error) throw new Error(data.error);
        changesOf[c.fullHash] = data;
        if (shownRow === c.row) renderChanges(c, data);
      })
      .catch(function () {
        if (shownRow !== c.row) return;
        detail.querySelector('.files').innerHTML = '<p class="empty">Changes could not be read. Run /gitgraph again to restart the helper.</p>';
      });
  }
  function counts(file) {
    return file.binary ? '<span class="num">binary</span>'
      : '<span class="num"><span class="add">+' + file.added + '</span><span class="del">−' + file.deleted + '</span></span>';
  }
  function renderChanges(c, data) {
    var count = detail.querySelector('.tabs .n');
    if (count) count.textContent = data.files.length;
    shownFile = 0;
    if (preferred && preferred.hash === c.fullHash) {
      data.files.some(function (file, index) {
        var isMatch = preferred.paths.indexOf(file.path) >= 0 || (file.from && preferred.paths.indexOf(file.from) >= 0);
        if (isMatch) shownFile = index;
        return isMatch;
      });
    }
    var note = data.isMerge ? '<p class="note">Merge commit: changes against its first parent.</p>' : '';
    if (!data.files.length) {
      detail.querySelector('.files').innerHTML = note + '<p class="empty">No file changes.</p>';
      detail.querySelector('.diff').innerHTML = '';
      return;
    }
    detail.querySelector('.files').innerHTML = note + data.files.map(function (file, index) {
      var slash = file.path.lastIndexOf('/');
      var title = file.from ? file.from + ' → ' + file.path : file.path;
      return '<div class="file' + (index === shownFile ? ' on' : '') + '" data-file="' + index + '" title="' + esc(title) + '">' +
        '<b class="st ' + file.status + '">' + file.status + '</b>' +
        '<span class="fp">' + esc(file.path.slice(slash + 1)) + (slash >= 0 ? '<span class="dir">' + esc(file.path.slice(0, slash)) + '</span>' : '') + '</span>' +
        counts(file) + '</div>';
    }).join('');
    renderDiff(data.files[shownFile]);
    var on = detail.querySelector('.file.on');
    if (on) on.scrollIntoView({ block: 'nearest' });
  }
  function renderDiff(file) {
    var title = file.from ? esc(file.from) + ' → ' + esc(file.path) : esc(file.path);
    var head = '<div class="dh"><b class="st ' + file.status + '">' + file.status + '</b>' + title + counts(file) + '</div>';
    if (file.binary) return (detail.querySelector('.diff').innerHTML = head + '<p class="empty">Binary file: no text changes to show.</p>');
    if (!file.hunks) return (detail.querySelector('.diff').innerHTML = head + '<p class="empty">' + (file.truncated ? 'Too large to show here.' : 'No text changes (mode or rename only).') + '</p>');
    // One card per hunk: a header naming its place in the file, then its lines.
    var old = 0, now = 0, cards = [], card = null;
    file.hunks.split('\n').forEach(function (line) {
      var row = function (kind, left, right) {
        card.lines.push('<div class="l' + kind + '"><span>' + left + '</span><span>' + right + '</span><code>' + esc(line) + '</code></div>');
      };
      var match = /^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@ ?(.*)$/.exec(line);
      if (match) {
        old = Number(match[1]); now = Number(match[3]);
        var size = match[4] === undefined ? 1 : Number(match[4]);
        var range = size === 0 ? 'removed at line ' + now : size === 1 ? 'Line ' + now : 'Lines ' + now + '–' + (now + size - 1);
        card = { title: 'Hunk ' + (cards.length + 1), range: range, context: match[5], lines: [] };
        cards.push(card);
      } else if (!card) {
        return;
      } else if (line[0] === '+') {
        row(' a', '', now++);
      } else if (line[0] === '-') {
        row(' d', old++, '');
      } else if (line[0] === ' ') {
        row('', old++, now++);
      } else if (line[0] === '\\') {
        row(' n', '', '');
      }
    });
    var html = cards.map(function (c) {
      return '<section class="hunk"><div class="hh"><b>' + c.title + '</b><span>' + c.range + '</span>' +
        (c.context ? '<code class="ctx" title="' + esc(c.context) + '">' + esc(c.context) + '</code>' : '') + '</div>' +
        '<div class="body"><div class="lines">' + c.lines.join('') + '</div></div></section>';
    });
    if (file.truncated) html.push('<p class="empty">Cut short: the rest of this file\'s changes are too large to show here.</p>');
    detail.querySelector('.diff').innerHTML = head + '<div class="hunks">' + html.join('') + '</div>';
    detail.querySelector('.diff').scrollTop = 0;
  }
  // The message as plain text, or as Markdown: the subject as a heading, the body as
  // written (Git bodies are already Markdown-like), list markers normalised to '-' and
  // the blank lines between list items dropped.
  function messageAs(c, format) {
    if (format === 'text') return c.subject + (c.body ? '\n\n' + c.body : '');
    var body = c.body.replace(/^(\s*)[*+] /gm, '$1- ').replace(/^(\s*- .*)\n\n(?=\s*- )/gm, '$1\n');
    return '### ' + c.subject + (body ? '\n\n' + body : '');
  }
  // Copies the Markdown twice over: as plain text (the source, for an editor or a
  // GitHub comment) and as HTML holding it in one <pre> code block, which rich editors
  // such as Slack's keep as a code block when pasted.
  function copyAsCodeBlock(markdown, label) {
    var html = '<pre><code>' + esc(markdown) + '</code></pre>';
    var listener = function (event) {
      event.clipboardData.setData('text/plain', markdown);
      event.clipboardData.setData('text/html', html);
      event.preventDefault();
    };
    document.addEventListener('copy', listener);
    var isCopied = false;
    try { isCopied = document.execCommand('copy'); } finally { document.removeEventListener('copy', listener); }
    if (isCopied) return show('Copied ' + label);
    if (window.ClipboardItem && navigator.clipboard && navigator.clipboard.write) {
      navigator.clipboard.write([new ClipboardItem({
        'text/plain': new Blob([markdown], { type: 'text/plain' }),
        'text/html': new Blob([html], { type: 'text/html' }),
      })]).then(function () { show('Copied ' + label); }, function () { copy(markdown, label); });
      return;
    }
    copy(markdown, label);
  }
  detail.addEventListener('click', function (e) {
    if (e.target.closest('.x')) return closeDetail();
    var tabButton = e.target.closest('.tabs button');
    if (tabButton) return showTab(tabButton.getAttribute('data-tab'));
    var fileRow = e.target.closest('.file');
    if (fileRow && shownRow >= 0) {
      var data = changesOf[commits[shownRow].fullHash];
      shownFile = Number(fileRow.getAttribute('data-file'));
      detail.querySelectorAll('.file').forEach(function (f) { f.classList.toggle('on', f === fileRow); });
      return renderDiff(data.files[shownFile]);
    }
    var pressed = e.target.closest('button[data-copy-as]');
    if (pressed && shownRow >= 0) {
      if (pressed.getAttribute('data-copy-as') === 'text') copy(messageAs(commits[shownRow], 'text'), 'the message as text');
      else copyAsCodeBlock(messageAs(commits[shownRow], 'markdown'), 'the message as a Markdown code block');
      pressed.classList.add('done');
      setTimeout(function () { pressed.classList.remove('done'); }, 1200);
      return;
    }
    var go = e.target.getAttribute('data-go'), copyText = e.target.getAttribute('data-copy');
    if (go !== null) { select(Number(go)); openDetail(commits[Number(go)]); }
    if (copyText !== null) copy(copyText, copyText.slice(0, 8));
  });
  detail.addEventListener('contextmenu', function (e) {
    if (shownRow < 0 || String(getSelection())) return;
    var c = commits[shownRow];
    openMenu(e, c.subject, both(c.hash, c.hash, 'hash').concat([['Copy full hash', function () { copy(c.fullHash, c.hash); }], null],
      both(c.subject + (c.body ? '\n\n' + c.body : ''), 'message', 'message'),
      both(c.author + ' <' + c.authorEmail + '>', c.author, 'author')));
  });
  document.addEventListener('keydown', function (e) { if (e.key === 'Escape' && menu.hidden) closeDetail(); });

  function onRowClick(e) {
    var row = e.target.closest('.r');
    if (!row) return;
    var c = commits[Number(row.getAttribute('data-row'))];
    if (e.target.classList.contains('h')) { copy(c.hash); select(c.row); return; }
    select(c.row);
    if (shownRow === c.row) return closeDetail();
    openCommit(c, row.classList.contains('fr') && flist.getAttribute('data-kind') === 'files');
  }
  // Opens a commit's details. From the file filter they open straight onto Changes, at the
  // first file that matched.
  function openCommit(c, fromFiles) {
    var isFiles = fromFiles && BRIDGE;
    preferred = isFiles ? { hash: c.fullHash, paths: fileMatches[c.fullHash] || [] } : null;
    if (isFiles) tab = 'changes';
    openDetail(c);
  }
  list.addEventListener('click', onRowClick);
  flist.addEventListener('click', onRowClick);

  // Keyboard: once a row has been clicked, the up and down arrows move to the previous or
  // next row of the list in view (the graph, or the file filter's results), opening each
  // one's details as they go, as stepping through the find box's results does. A click
  // anywhere else (the details, the sidebar, the header) hands the arrows back.
  var isListActive = false;
  document.addEventListener('mousedown', function (e) {
    isListActive = !!(e.target.closest && e.target.closest('#list, #flist'));
  });
  document.addEventListener('keydown', function (e) {
    if (!isListActive || (e.key !== 'ArrowDown' && e.key !== 'ArrowUp') || !selected) return;
    if (e.target.closest && e.target.closest('input, textarea')) return;
    var step = e.key === 'ArrowDown' ? 1 : -1;
    if (selected.classList.contains('fr')) {
      var index = filterHits.indexOf(Number(selected.getAttribute('data-row'))) + step;
      if (index < 0 || index >= filterHits.length) return;
      e.preventDefault();
      return stepFiltered(index);
    }
    var row = Number(selected.getAttribute('data-row')) + step;
    if (row < 0 || row >= commits.length) return;
    e.preventDefault();
    select(row);
    openCommit(commits[row], false);
  });
  function onRowMenu(e) {
    var row = e.target.closest('.r');
    if (!row) return;
    var c = commits[Number(row.getAttribute('data-row'))];
    select(c.row);
    var items = both(c.hash, c.hash, 'hash').concat(
      [['Copy full hash', function () { copy(c.fullHash, c.hash); }], null],
      both(c.subject, 'subject', 'subject'));
    c.branches.concat(c.remotes, c.tags).forEach(function (name) {
      items = items.concat([null], both(name, name, name));
    });
    openMenu(e, c.subject, items);
  }
  list.addEventListener('contextmenu', onRowMenu);
  flist.addEventListener('contextmenu', onRowMenu);

  // Find, in two modes, both listing only the matching commits in place of the graph.
  // Commits: subject, author, hash or ref contain the text. Files: the commit changed a
  // file whose path contains it (the bridge reads that with git), its matching paths shown.
  var find = document.getElementById('find'), counter = document.getElementById('count');
  var modes = document.getElementById('modes'), mode = 'commits';
  var fileMatches = {}, fileTimer = null, fileQuery = 0, filterHits = [], filterAt = -1;
  if (!BRIDGE) {
    var filesButton = modes.querySelector('[data-mode="files"]');
    filesButton.disabled = true;
    filesButton.title = 'Needs the gitgraph helper: run /gitgraph again';
  }
  function setCount(text) {
    counter.textContent = text;
    find.classList.toggle('has', !!text);
  }
  function clearFiles() {
    flist.hidden = true;
    list.hidden = false;
    flist.innerHTML = '';
    flist.removeAttribute('data-kind');
    fileMatches = {};
    filterHits = [];
    filterAt = -1;
  }
  function showFiltered(kind, hits, pathsOf, empty) {
    filterHits = hits.map(function (c) { return c.row; });
    filterAt = -1;
    flist.setAttribute('data-kind', kind);
    flist.innerHTML = hits.length ? hits.map(function (c) {
      var paths = pathsOf ? pathsOf(c) : null;
      var shown = paths ? paths.slice(0, 2).join(', ') + (paths.length > 2 ? ' +' + (paths.length - 2) : '') : '';
      var pills = paths ? '' : c.refs.map(function (r) {
        return '<span class="p ' + r.kind + '" style="color:' + colour(c.lane) + '">' + esc(r.kind === 'tag' ? '⌂ ' + r.label : r.label) + '</span>';
      }).join('');
      return '<div class="r fr' + (c.isHead ? ' head' : '') + '" data-row="' + c.row + '">' +
        '<i class="dot" style="background:' + colour(c.lane) + '"></i>' +
        '<span class="s" title="' + esc(c.subject) + '">' + esc(c.subject) + '</span>' + pills +
        (paths ? '<span class="paths" title="' + esc(paths.join('\n')) + '">' + esc(shown) + '</span>' : '') +
        '<span class="a">' + esc(c.author) + (c.isCommittedByOther ? '*' : '') + '</span>' +
        '<span class="d">' + when(c.time) + '</span><span class="h" title="Click to copy">' + c.hash + '</span></div>';
    }).join('') : '<p class="none">' + empty + '</p>';
    list.hidden = true;
    flist.hidden = false;
    flist.scrollTop = 0;
    setCount(hits.length + (hits.length === 1 ? ' commit' : ' commits'));
  }
  function findCommits() {
    var needle = find.value.trim().toLowerCase();
    if (!needle) { clearFiles(); setCount(''); return; }
    var hits = commits.filter(function (c) {
      return (c.subject + ' ' + c.author + ' ' + c.fullHash + ' ' + c.branches.join(' ') + ' ' + c.remotes.join(' ') + ' ' + c.tags.join(' ')).toLowerCase().indexOf(needle) >= 0;
    });
    showFiltered('commits', hits, null, 'No commit matches “' + esc(find.value.trim()) + '”.');
  }
  function findFiles() {
    var needle = find.value.trim();
    clearTimeout(fileTimer);
    if (!needle) { clearFiles(); setCount(''); return; }
    setCount('…');
    var ticket = ++fileQuery;
    fileTimer = setTimeout(function () {
      fetch('/touching?repo=' + encodeURIComponent(BRIDGE.repo) + '&q=' + encodeURIComponent(needle))
        .then(function (response) {
          if (response.status === 404) throw new Error('outdated');
          return response.json();
        })
        .then(function (data) {
          if (ticket !== fileQuery || mode !== 'files') return;
          if (data.error) throw new Error(data.error);
          fileMatches = data.matches;
          var hits = commits.filter(function (c) { return fileMatches[c.fullHash]; });
          showFiltered('files', hits, function (c) { return fileMatches[c.fullHash]; },
            'No commit changed a file whose path contains “' + esc(needle) + '”.');
        })
        .catch(function (error) {
          if (ticket !== fileQuery) return;
          setCount('unavailable');
          list.hidden = true;
          flist.hidden = false;
          flist.innerHTML = '<p class="none">' + (String(error.message) === 'outdated'
            ? 'The gitgraph helper running now is older than this page. Run /gitgraph again to update it.'
            : 'The gitgraph helper did not answer. Run /gitgraph again to restart it.') + '</p>';
        });
    }, 220);
  }
  function runFind() { if (mode === 'files') findFiles(); else findCommits(); }
  modes.addEventListener('click', function (e) {
    var button = e.target.closest('button');
    if (!button || button.disabled || button.getAttribute('data-mode') === mode) return;
    mode = button.getAttribute('data-mode');
    modes.querySelectorAll('button').forEach(function (b) { b.classList.toggle('on', b === button); });
    find.placeholder = mode === 'files' ? 'Find files: part of a path or file name' : 'Find commits: subject, author, hash or ref';
    clearFiles();
    runFind();
    find.focus();
  });
  find.addEventListener('input', runFind);
  // Moves to a filtered result: selects it and opens its details, on Changes at the
  // matching file when the filter is by file.
  function stepFiltered(index) {
    filterAt = index;
    var c = commits[filterHits[index]];
    select(c.row);
    openCommit(c, flist.getAttribute('data-kind') === 'files');
    setCount((index + 1) + ' / ' + filterHits.length);
  }
  // Enter / Shift+Enter (or the arrow keys) step through the results.
  find.addEventListener('keydown', function (e) {
    if (e.key === 'Escape' && find.value) { find.value = ''; runFind(); return; }
    var step = e.key === 'Enter' ? (e.shiftKey ? -1 : 1) : e.key === 'ArrowDown' ? 1 : e.key === 'ArrowUp' ? -1 : 0;
    if (!step || !filterHits.length) return;
    e.preventDefault();
    stepFiltered((filterAt + step + filterHits.length) % filterHits.length);
  });

  // Resizing: drag the sidebar edge, the details panel's top edge, or the line between its
  // columns. Sizes are kept per browser for the next page.
  var root = document.documentElement, sizes = {};
  try { sizes = JSON.parse(localStorage.getItem('gitgraph-layout') || '{}') || {}; } catch (error) { sizes = {}; }
  function apply() {
    if (sizes.nav) root.style.setProperty('--nav-w', sizes.nav + 'px');
    if (sizes.detail) root.style.setProperty('--detail-h', sizes.detail + 'px');
    if (sizes.meta) root.style.setProperty('--meta-w', sizes.meta + 'px');
    if (sizes.files) root.style.setProperty('--files-w', sizes.files + 'px');
  }
  apply();
  var clamp = function (value, low, high) { return Math.max(low, Math.min(high, value)); };
  document.addEventListener('pointerdown', function (e) {
    var grip = e.target.closest && e.target.closest('.grip');
    if (!grip) return;
    e.preventDefault();
    var kind = grip.getAttribute('data-resize'), main = document.querySelector('.main');
    grip.classList.add('on');
    grip.setPointerCapture(e.pointerId);
    function move(event) {
      if (kind === 'nav') sizes.nav = clamp(event.clientX, 160, innerWidth - 480);
      if (kind === 'detail') sizes.detail = clamp(main.getBoundingClientRect().bottom - event.clientY, 120, main.clientHeight - 160);
      if (kind === 'meta') sizes.meta = clamp(event.clientX - detail.getBoundingClientRect().left, 220, detail.clientWidth - 220);
      if (kind === 'files') sizes.files = clamp(event.clientX - detail.getBoundingClientRect().left, 200, detail.clientWidth - 260);
      apply();
    }
    function up() {
      grip.classList.remove('on');
      grip.removeEventListener('pointermove', move);
      grip.removeEventListener('pointerup', up);
      try { localStorage.setItem('gitgraph-layout', JSON.stringify(sizes)); } catch (error) { /* sizes stay for this page */ }
    }
    grip.addEventListener('pointermove', move);
    grip.addEventListener('pointerup', up);
  });

  // Dark by default; the header button switches, and this browser remembers the choice.
  document.getElementById('mode').addEventListener('click', function () {
    var isLight = root.getAttribute('data-theme') !== 'light';
    if (isLight) root.setAttribute('data-theme', 'light'); else root.removeAttribute('data-theme');
    try { localStorage.setItem('gitgraph-theme', isLight ? 'light' : 'dark'); } catch (error) { /* the choice lasts this page */ }
  });

  var head = commits.filter(function (c) { return c.isHead; })[0];
  if (head && head.row > 20) select(head.row);
})();
`

const SUN =
  '<svg class="sun" viewBox="0 0 24 24"><circle cx="12" cy="12" r="4"/>' +
  '<path d="M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4"/></svg>'
const MOON = '<svg class="moon" viewBox="0 0 24 24"><path d="M20 14.5A8 8 0 1 1 9.5 4a6.5 6.5 0 0 0 10.5 10.5z"/></svg>'

/**
 * A self-contained page for the whole history: a refs tree on the left
 * (branches, remotes, tags; click jumps to the latest commit, right-click
 * copies the full name), the graph with subject, refs, author, date and hash
 * per commit in one scroll, a details panel a row click opens, and a find box.
 * With `bridge`, right-click menus also add a name or hash to the prompt. The data rides in the page as
 * JSON, escaped so it cannot close the script element.
 */
export function buildPage(
  graph: GitGraph,
  generatedAt: string,
  bridge: { session: string; token: string; repo: string } | null,
): string {
  const data = JSON.stringify({ commits: graph.commits, edges: graph.edges }).replace(/</g, '\\u003c')
  const title = graph.repository.replace(/[&<>"]/g, character => `&#${character.charCodeAt(0)};`)
  const truncated = graph.isTruncated ? ' most recent' : ''

  return (
    '<!doctype html><html><head><meta charset="utf-8">' +
    `<title>Git graph · ${title}</title><style>${STYLE}</style>` +
    // Dark unless this browser chose light before; set before the body draws, so no flash.
    "<script>try{if(localStorage.getItem('gitgraph-theme')==='light')document.documentElement.setAttribute('data-theme','light')}catch(error){}</script>" +
    '</head><body><header>' +
    `<strong>${title}</strong><span>${graph.commits.length}${truncated} commits · generated ${generatedAt} · run /gitgraph again to refresh</span>` +
    '<div class="find"><div class="modes" id="modes">' +
    '<button data-mode="commits" class="on" title="Find commits by subject, author, hash or ref">Commits</button>' +
    '<button data-mode="files" title="Show only the commits that changed a file whose path contains the text">Files</button></div>' +
    '<div class="box"><input id="find" placeholder="Find commits: subject, author, hash or ref" autocomplete="off">' +
    '<span class="count" id="count"></span></div></div>' +
    `<button class="mode" id="mode" title="Switch between dark and light">${SUN}${MOON}</button></header>` +
    '<div class="app"><nav id="refs"></nav><div class="grip v" data-resize="nav"></div><div class="main">' +
    '<div id="list"></div><div id="flist" hidden></div><div id="detail" hidden></div></div></div>' +
    '<div id="menu" hidden></div><div id="toast" hidden></div>' +
    `<script>var DATA = ${data}; var PALETTE = ${JSON.stringify(PALETTE)}; var BRIDGE = ${JSON.stringify(bridge)};</script>` +
    `<script>${SCRIPT}</script></body></html>`
  )
}
