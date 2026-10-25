// Utilidades compartilhadas entre as páginas.
window.EB = (() => {
  const UFS = {br:'Brasil',ac:'Acre',al:'Alagoas',am:'Amazonas',ap:'Amapá',ba:'Bahia',ce:'Ceará',df:'Distrito Federal',es:'Espírito Santo',go:'Goiás',ma:'Maranhão',mg:'Minas Gerais',ms:'Mato Grosso do Sul',mt:'Mato Grosso',pa:'Pará',pb:'Paraíba',pe:'Pernambuco',pi:'Piauí',pr:'Paraná',rj:'Rio de Janeiro',rn:'Rio Grande do Norte',ro:'Rondônia',rr:'Roraima',rs:'Rio Grande do Sul',sc:'Santa Catarina',se:'Sergipe',sp:'São Paulo',to:'Tocantins',zz:'Exterior'};
  const CARGOS = {1:'Presidente',3:'Governador',5:'Senador',6:'Deputado federal',7:'Deputado estadual',8:'Deputado distrital',11:'Prefeito',13:'Vereador'};
  const ORD = [1,3,5,6,7,8,11,13];
  // Apuração ao vivo: a home só destaca o placar dentro desta janela.
  const LIVE = {ate: new Date('2026-10-27T23:59:00-03:00'), base:'/tse/ele2026', fed:'6258', titulo:'2º turno 2026'};
  const esc = s => String(s ?? '').replace(/[&<>"]/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
  const fmt = x => Math.round(+x || 0).toLocaleString('pt-BR');
  const pc = (x, d = 1) => (isFinite(x) ? +x : 0).toLocaleString('pt-BR', {minimumFractionDigits:d, maximumFractionDigits:d}) + '%';
  const title = s => String(s ?? '').toLowerCase().replace(/(^|[\s'-])(\S)/g, (m, a, b) => a + b.toUpperCase()).replace(/\b(Da|De|Do|Dos|Das|E|D')\b/g, w => w.toLowerCase());
  const norm = s => String(s ?? '').normalize('NFD').replace(/[̀-ͯ]/g, '').toLowerCase().trim();
  const cache = {};
  const getJ = p => cache[p] || (cache[p] = fetch(p).then(r => { if (!r.ok) throw new Error('arquivo não encontrado'); return r.json(); }));
  const favs = {
    list(){ try { return JSON.parse(localStorage.getItem('eb_favs') || '[]'); } catch(e){ return []; } },
    has(cd){ return this.list().some(f => f.cd === cd); },
    toggle(item){ const l = this.list(); const i = l.findIndex(f => f.cd === item.cd); if (i >= 0) l.splice(i, 1); else l.unshift(item);
      try { localStorage.setItem('eb_favs', JSON.stringify(l.slice(0, 20))); } catch(e){} return i < 0; }
  };
  const munUrl = (cd, uf) => `municipio.html?cd=${encodeURIComponent(cd)}&uf=${encodeURIComponent(uf)}`;
  // Busca de município com índice data/mun/index.json -> {cd:[nome, uf]}
  async function munIndex(){ const ix = await getJ('data/mun/index.json'); return Object.entries(ix).map(([cd,[nm,uf]]) => ({cd, nm:title(nm), uf, k:norm(nm)})); }
  function search(list, q, n = 8){
    q = norm(q); if (!q) return [];
    const starts = [], has = [];
    for (const m of list){ if (m.k.startsWith(q)) starts.push(m); else if (m.k.includes(q)) has.push(m); }
    const byPop = (a, b) => a.nm.length - b.nm.length || a.nm.localeCompare(b.nm);
    return starts.sort(byPop).concat(has.sort(byPop)).slice(0, n);
  }
  return {UFS, CARGOS, ORD, LIVE, esc, fmt, pc, title, norm, getJ, favs, munUrl, munIndex, search};
})();
