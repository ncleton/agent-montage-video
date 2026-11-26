// Tournées de la semaine S50 (7 au 11 décembre 2026) du compte de démonstration : un passage par jour sur une fiche
// localisée du portail HubSpot de test, ordre et route calculés par le routeur local. Sans elles, le panneau des jours
// de S50 affiche « Prévu, pas encore de tournée » (état vide refusé par studio_check). Relançable : un jour déjà
// semé est seulement recalculé.
//   node seed/seed_tours_decembre.mjs        (depuis studios/bigup, sous le verrou data/tournage.lock)
import { call } from './call.mjs';
const send = (tool, args = {}) => call('commercial', tool, args, 'site');
const schedule = [
  ['2026-12-07', 'GRAAL'], ['2026-12-08', 'COLLEGE FRANKLIN'], ['2026-12-09', 'ALTEREOS'],
  ['2026-12-10', 'BASIS ELECTRONIQUE'], ['2026-12-11', 'CERBALLIANCE NORD-PAS-DE-CALAIS'],
];
const list = await send('list_itineraries');
for (const [day, name] of schedule) {
  const search = await send('search_tour_companies', { data: { query: name } });
  const hit = search.hubspot.results.find((r) => r.company.includes(name));
  if (!hit || new URL(hit.url).pathname.split('/')[2] !== '149831332' || !hit.latitude || !hit.longitude) throw new Error('Il manque une fiche de test localisée pour ' + name);
  const title = 'Studio Bigup · métropole lilloise · ' + day;
  const existing = list.find((t) => t.title === title);
  let itinerary = existing ? await send('get_itinerary', { id: existing.id })
    : await send('create_itinerary', { idempotency_key: 'studio-tournees-' + day, data: { title, days: [day] } });
  if (!itinerary.stops.length) {
    itinerary = await send('add_itinerary_stop', { id: itinerary.id, expected_revision: itinerary.revision, idempotency_key: 'studio-tournees-stop-' + day,
      data: { hubspot_company: { id: hit.hubspot_id }, day, added_from: 'manual', note: 'Passage de démonstration.' } });
  }
  if (!itinerary.solution || itinerary.solution_stale) {
    itinerary = await send('optimize_itinerary', { id: itinerary.id, expected_revision: itinerary.revision, idempotency_key: crypto.randomUUID(), data: {} });
  }
  if (!itinerary.solution || itinerary.solution_stale) throw new Error('Itinéraire non calculé le ' + day);
  console.log(day, hit.company, itinerary.stops.length + ' arrêt', JSON.stringify(itinerary.solution.summary));
}

