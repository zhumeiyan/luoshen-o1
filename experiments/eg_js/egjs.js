/* ================================================================
   evalguard JS engine — 页面内嵌版（与 docs/demo.html 同源，勿手改副本）
   ----------------------------------------------------------------
   设计原则（对应我们自己的失败模式库）：
     1. 只实现【语法类】规则 —— 129 号实测：语法类命中 18/20，
        方法论类 1/55。方法论类已关停，此处默认不启用。
     2. 每条规则都能说清「它抓的是什么静默失败」，不是风格意见。
     3. 关停的规则仍然列出来、仍然可勾选 —— 让你看见我关了什么。
   ================================================================ */
'use strict';

var EG_RULES = [
  {
    id: 'EG006', sev: 'blocker', cls: 'syntax', on: true,
    title: 'Bare / silent except 吞掉了本该报告的失败',
    why: '异常被吃掉之后，脚本照样退出码 0。你看到的是"跑完了"，不是"跑通了"。',
    fix: '换成 except SpecificError，并记录或重抛。',
    run: function (L) {
      var out = [];
      L.forEach(function (s, i) {
        if (/^\s*except\s*:/.test(s) || /except\s*:?\s*(pass|\.\.\.)\s*$/.test(s))
          out.push({ line: i + 1, code: s.trim() });
      });
      return out;
    }
  },
  {
    id: 'EG005', sev: 'warn', cls: 'syntax', on: true,
    title: '除法没有分母保护',
    why: '分母为 0 时，多数运行时不抛异常而是产出 inf/NaN，指标照样打印出来。',
    fix: '除前判空，或用 max(den, 1) 显式兜底。',
    run: function (L) {
      var out = [];
      // 先扫一遍"被保护过的名字"：assert n>0 / if not n / if n==0 / max(n,1)
      // （验证时撞到的真实假阳性：clean_ok.py 有 assert len(gold)>0 仍被报，
      //   这正是 129 号记过的老毛病——把「修好的样子」当成问题）
      var guarded = {};
      var all = L.join('\n');
      var gm = all.match(/(?:assert|if)\s+(?:not\s+)?([A-Za-z_][A-Za-z0-9_.]*)\s*(?:==\s*0|>\s*0|<=\s*0|is\s+None)?/g) || [];
      gm.forEach(function (g) {
        var m = g.match(/([A-Za-z_][A-Za-z0-9_.]*)\s*(?:==\s*0|>\s*0|<=\s*0|is\s+None)?\s*$/);
        if (m) guarded[m[1]] = true;
      });
      (all.match(/max\s*\(\s*([A-Za-z_][A-Za-z0-9_.]*)\s*,/g) || []).forEach(function (g) {
        var m = g.match(/max\s*\(\s*([A-Za-z_][A-Za-z0-9_.]*)/); if (m) guarded[m[1]] = true;
      });
      L.forEach(function (s, i) {
        // 先剥掉注释，再剥掉字符串字面量 —— URL / 路径里的 "/" 不是除法
        // （验证时撞到的真实假阳性：fetch("https://a.b/c.json") 被当成除法）
        var t = s.replace(/#[^\n]*/, '')
                 .replace(/"""[\s\S]*?"""/g, '""')
                 .replace(/'''[\s\S]*?'''/g, "''")
                 .replace(/(['"])(?:\\.|(?!\1)[^\\])*\1/g, '""');
        var m = t.match(/\/\s*\(?\s*([A-Za-z_][A-Za-z0-9_.]*)/g);
        if (!m) return;
        // 分母是纯数字常量则不算（0.5 这类常量除法是安全的）
        var bare = m.filter(function (x) { return !/^\/\s*\(?\s*\d/.test(x); })
                    .map(function (x) { var q = x.match(/([A-Za-z_][A-Za-z0-9_.]*)\s*$/); return q ? q[1] : ''; })
                    .filter(function (v) { return v && !guarded[v]; });
        if (bare.length) out.push({ line: i + 1, code: s.trim() });
      });
      return out;
    }
  },
  {
    id: 'EG001', sev: 'warn', cls: 'syntax', on: true,
    title: '用了随机 API，但全程没有 seed',
    why: '每次跑出来的数字都不一样，你无法区分"方法有效"和"这次运气好"。',
    fix: '入口处固定 seed，并把 seed 写进结果文件。',
    run: function (L) {
      var src = L.join('\n');
      var uses = /(\brandom\.|\bnp\.random\.|\bnumpy\.random\.|\btorch\.rand|\bshuffle\s*\()/.test(src);
      var seed = /(seed\s*\(|manual_seed|random_state\s*=)/.test(src);
      if (uses && !seed) {
        var hit = [];
        L.forEach(function (s, i) {
          if (/(\brandom\.|\bnp\.random\.|\bnumpy\.random\.|\btorch\.rand|\bshuffle\s*\()/.test(s))
            hit.push({ line: i + 1, code: s.trim() });
        });
        return hit.slice(0, 5);
      }
      return [];
    }
  },
  {
    id: 'EG009', sev: 'warn', cls: 'syntax', on: true,
    title: '赋值后再没被用过（静默死变量）',
    why: '最常见的情况是"算了一半忘了接上"，脚本照样跑完、照样出数。',
    fix: '接上它，或者删掉。别让它留在那里假装工作已完成。',
    run: function (L) {
      var src = L.join('\n'), out = [];
      L.forEach(function (s, i) {
        var m = s.match(/^\s*([a-z_][A-Za-z0-9_]{2,})\s*=\s*(?!==)/);
        if (!m) return;
        var v = m[1];
        if (/^(self|cls)$/.test(v)) return;
        var n = (src.match(new RegExp('(?<![A-Za-z0-9_])' + v + '(?![A-Za-z0-9_])', 'g')) || []).length;
        if (n <= 1) out.push({ line: i + 1, code: s.trim() });
      });
      return out;
    }
  },
  {
    id: 'EG007', sev: 'warn', cls: 'syntax', on: true,
    title: '声称"已保存/已归档"，但全文没有写调用',
    why: '汇报里说结果落盘了，代码里没有 open(...,"w") / json.dump / to_csv。',
    fix: '补上真实的写调用，或改掉措辞。',
    run: function (L) {
      var src = L.join('\n');
      var claims = /(saved|archived|dumped|persisted|written to|已保存|已归档|已落盘|已写入)/i.test(src);
      var writes = /(open\s*\([^)]*['"][wa]|json\.dump|\.write\s*\(|to_csv|to_excel|to_json|save\s*\(|np\.save|torch\.save)/.test(src);
      if (claims && !writes) {
        var hit = [];
        L.forEach(function (s, i) {
          if (/(saved|archived|dumped|persisted|written to|已保存|已归档|已落盘|已写入)/i.test(s))
            hit.push({ line: i + 1, code: s.trim() });
        });
        return hit.slice(0, 4);
      }
      return [];
    }
  },
  {
    id: 'EG003', sev: 'warn', cls: 'syntax', on: true,
    title: '判定阈值硬编码成 magic number',
    why: '阈值来源说不清，结论就不可复核；换个数据集还是这个数。',
    fix: '提到具名常量/配置，并注明它是怎么定的。',
    run: function (L) {
      var out = [];
      L.forEach(function (s, i) {
        var t = s.replace(/#[^\n]*/, '');
        // 分成「赋给具名常量」和「直接内联在比较里」两种。
        // 前者恰恰是本规则要求的修好形态 —— 报它就是惩罚好代码
        // （验证时撞到的真实假阳性：THRESHOLD = 0.5 被当 magic number，
        //   与 129 号 EG002 的旧病同型：well-named code 反而中招）
        var named = /^\s*[A-Z][A-Z0-9_]*\s*=\s*[0-9.]+/.test(t);
        var inlineMagic = /[<>]=?\s*0\.\d{2,}/.test(t) && !named;
        var anonAssign = /(threshold|thresh|cutoff|cut_off|tolerance)\s*[:=]\s*[0-9.]+/i.test(t) && !named;
        if (inlineMagic || anonAssign) out.push({ line: i + 1, code: s.trim() });
      });
      return out;
    }
  },

  /* ---------- 以下为【方法论类】：129 号实测 1/55，已关停 ---------- */
  {
    id: 'EG002', sev: 'blocker', cls: 'method', on: false,
    title: '报了 accuracy/recall，但没有随机基线',
    why: '没有基线，你无法判断 0.72 是好是坏——多数类问题里 majority 就能到 0.7。',
    fix: '同时报 majority / random 基线，让提升量可解释。',
    run: function (L) {
      var src = L.join('\n');
      var rep = /\b(acc|accuracy|recall|precision|f1)\b/i.test(src);
      var base = /(baseline|majority|dummy|random|chance|most_common)/i.test(src);
      if (rep && !base) {
        var hit = [];
        L.forEach(function (s, i) {
          if (/\b(acc|accuracy|recall|precision|f1)\b/i.test(s)) hit.push({ line: i + 1, code: s.trim() });
        });
        return hit.slice(0, 4);
      }
      return [];
    }
  },
  {
    id: 'EG013', sev: 'warn', cls: 'method', on: false,
    title: '比率指标没带分子分母',
    why: '"成功率 93%" 在 n=14 和 n=14000 上含义完全不同，没有 n 就是不可判定的。',
    fix: '把分子与分母一起写进结果。',
    run: function (L) {
      var src = L.join('\n');
      var rep = /(rate|ratio|percent|pct|accuracy)/i.test(src);
      var cnt = /(count|n_|num_|total|denominator|len\s*\()/i.test(src);
      if (rep && !cnt) {
        var hit = [];
        L.forEach(function (s, i) {
          if (/(rate|ratio|percent|pct)/i.test(s)) hit.push({ line: i + 1, code: s.trim() });
        });
        return hit.slice(0, 3);
      }
      return [];
    }
  },
  {
    id: 'EG016', sev: 'blocker', cls: 'method', on: false,
    title: '结论依赖外部通道，且没有可达性重测',
    why: '外网取数失败时你的分支会静默走空值，结论建立在一次没人复核的抓取上。',
    fix: '抓取后重测可达性/非空，失败即中止而不是降级。',
    run: function (L) {
      var src = L.join('\n');
      var net = /(urlopen|requests\.|httpx\.|curl|fetch\s*\()/.test(src);
      var rechk = /(returncode|status_code|raise_for_status|\.ok\b|reachab|is_reachable)/.test(src);
      if (net && !rechk) {
        var hit = [];
        L.forEach(function (s, i) {
          if (/(urlopen|requests\.|httpx\.|fetch\s*\()/.test(s)) hit.push({ line: i + 1, code: s.trim() });
        });
        return hit.slice(0, 3);
      }
      return [];
    }
  }
];

function egScan(src, opts) {
  opts = opts || {};
  var L = String(src == null ? '' : src).split(/\r?\n/);
  var out = [];
  EG_RULES.forEach(function (r) {
    var on = (opts[r.id] === undefined) ? r.on : !!opts[r.id];
    if (!on) return;
    var hits = [];
    try { hits = r.run(L) || []; } catch (e) { hits = []; }
    if (hits.length) out.push({ id: r.id, sev: r.sev, cls: r.cls, title: r.title,
                                why: r.why, fix: r.fix, hits: hits });
  });
  var c = { blocker: 0, warn: 0, info: 0 };
  out.forEach(function (f) { c[f.sev] += f.hits.length; });
  return { findings: out, counts: c, lines: L.length };
}

if (typeof module !== 'undefined' && module.exports) {
  module.exports = { egScan: egScan, EG_RULES: EG_RULES };
}
