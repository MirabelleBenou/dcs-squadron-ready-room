/* ===================================================================
   DCS Squadron Ready Room — Front réel (Lot 3b)
   Maquette validée (DA figée) branchée sur l'API + SSE. Toute donnée
   factice a été retirée : tout ce qui s'affiche vient de /api/*.
   =================================================================== */
(function(){
"use strict";

/* ---------- Icônes SVG (DA validée, inchangées) ---------- */
const SVG_PIP_PRESENT = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor" role="img" aria-label="Présent">
  <mask id="glyph">
    <rect width="24" height="24" fill="#fff"></rect>
    <path d="M8 12.3 10.9 15.3 16.2 9" fill="none" stroke="#000" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"></path>
  </mask>
  <circle cx="12" cy="12" r="9.5" opacity="0.16"></circle>
  <circle cx="12" cy="12" r="6.6" opacity="0.28"></circle>
  <circle cx="12" cy="12" r="6.6" mask="url(#glyph)"></circle>
</svg>`;
const SVG_PIP_MAYBE = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor" role="img" aria-label="Peut-être">
  <mask id="glyph">
    <rect width="24" height="24" fill="#fff"></rect>
    <path d="M8.4 12.9c1.1-1.5 2.3-1.6 3.6-.8s2.5.7 3.6-.8" fill="none" stroke="#000" stroke-width="2.1" stroke-linecap="round" stroke-linejoin="round"></path>
  </mask>
  <circle cx="12" cy="12" r="9.5" opacity="0.16"></circle>
  <circle cx="12" cy="12" r="6.6" opacity="0.28"></circle>
  <circle cx="12" cy="12" r="6.6" mask="url(#glyph)"></circle>
</svg>`;
const SVG_PIP_ABSENT = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor" role="img" aria-label="Absent">
  <mask id="glyph">
    <rect width="24" height="24" fill="#fff"></rect>
    <path d="M8.6 8.6 15.4 15.4 M15.4 8.6 8.6 15.4" fill="none" stroke="#000" stroke-width="2.2" stroke-linecap="round"></path>
  </mask>
  <circle cx="12" cy="12" r="9.5" opacity="0.16"></circle>
  <circle cx="12" cy="12" r="6.6" opacity="0.28"></circle>
  <circle cx="12" cy="12" r="6.6" mask="url(#glyph)"></circle>
</svg>`;
/* Icônes inline dédiées Révision ④.1 (chgt 1 dépli roster / chgt 4
   suppression admin) -- volontairement PAS ajoutées au sprite de
   index.html (fichier intouché, brief §Interdits/DoD). Même discipline
   que le sprite Débrief : fill:none/stroke:currentColor via la classe
   globale .ic, viewBox 24, traits arrondis, aucun texte/emoji. */
const SVG_ICON_TRASH = `<svg class="ic" viewBox="0 0 24 24"><path d="M5 7h14M9 7V5a1 1 0 0 1 1-1h4a1 1 0 0 1 1 1v2"/><path d="M7 7l1 13a1 1 0 0 0 1 1h6a1 1 0 0 0 1-1l1-13"/><path d="M10 11v6M14 11v6"/></svg>`;
const SVG_ICON_CHEVRON = `<svg class="ic group-chevron" viewBox="0 0 24 24"><path d="M8 5l8 7-8 7"/></svg>`;
const SVG_TYPE_ENTRAINEMENT = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round" role="img" aria-label="Entraînement">
  <circle cx="12" cy="12" r="7.25"></circle>
  <circle cx="12" cy="12" r="2.7"></circle>
  <line x1="12" y1="1.9" x2="12" y2="5.6"></line>
  <line x1="12" y1="18.4" x2="12" y2="22.1"></line>
  <line x1="1.9" y1="12" x2="5.6" y2="12"></line>
  <line x1="18.4" y1="12" x2="22.1" y2="12"></line>
</svg>`;
const SVG_TYPE_MISSION = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round" role="img" aria-label="Mission">
  <path d="M12 2.4 13.55 10.45 21.6 12 13.55 13.55 12 21.6 10.45 13.55 2.4 12 10.45 10.45 Z"></path>
  <circle cx="12" cy="12" r="1.5"></circle>
</svg>`;
const SVG_TYPE_JEULIBRE = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round" role="img" aria-label="Jeu libre">
  <circle cx="12" cy="6.6" r="2.9"></circle>
  <line x1="12" y1="9.5" x2="12" y2="17.4"></line>
  <rect x="5.8" y="17.2" width="12.4" height="3.6" rx="1.8"></rect>
  <line x1="8.6" y1="20.8" x2="8" y2="22.1"></line>
  <line x1="15.4" y1="20.8" x2="16" y2="22.1"></line>
</svg>`;
const SVG_TYPE_CAMPAGNE = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round" role="img" aria-label="Campagne"><path d="M4 22V3"/><path d="M4 3h13l-2.5 4L17 11H4"/></svg>`;

const TYPE_ICON = {entrainement:SVG_TYPE_ENTRAINEMENT, mission:SVG_TYPE_MISSION, jeulibre:SVG_TYPE_JEULIBRE, campagne:SVG_TYPE_CAMPAGNE};
const TYPE_VAR = {entrainement:"--type-entrainement", mission:"--type-mission", jeulibre:"--type-jeulibre", campagne:"--type-campagne"};
// Lot « Ma réponse sur la Planche » (v1.0073) : la pastille « à répondre » — cercle pointillé, « ? » au trait, sans masque.
const SVG_PIP_TODO = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" role="img" aria-label="À répondre">
  <circle cx="12" cy="12" r="8.6" stroke-width="1.5" stroke-dasharray="2.6 2.2"></circle>
  <path d="M9.7 9.7a2.4 2.4 0 1 1 3.5 2.2c-.8.5-1.2.9-1.2 1.8" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round"></path>
  <circle cx="12" cy="16.3" r="1" fill="currentColor" stroke="none"></circle>
</svg>`;
const PIP_RAW = {present:SVG_PIP_PRESENT, maybe:SVG_PIP_MAYBE, absent:SVG_PIP_ABSENT, todo:SVG_PIP_TODO};

/* ---------- Preferences RSVP (Lot 6) : appareils + types de mission ----------
   Listes figees, cf. SPEC_READY_ROOM_Escadrilles_et_RSVP_v1 §B.3. Doivent
   rester en phase avec AIRCRAFT_CODES / MISSION_TYPE_CODES cote backend
   (app/schemas.py) -- toute divergence ferait rejeter en 422 des valeurs
   pourtant proposees par ce menu. */
const AIRCRAFT_CODES = [
  "A-10A","AH-64","AJS-37","C-101","C-130","CH-47","F-100","F-14A","F-14B",
  "F-15C","F-16C","F/A-18","F-4E","F-5E","L-39","MB-339","Mi-24P","Mi-8",
  "MIG-21Bis","MIG-29 FC3","MIG-29 FF","Mirage F1 CE","Mirage F1 EE",
  "OH-58D","SA-342 Gazelle","SU-25","SU-27","UH-1H",
  "Combined Arms (JTAC)","LotATC"
];
const MISSION_TYPES = [
  {code:"CAP", fr:"CAP", en:"CAP"},
  {code:"STRIKE", fr:"Strike", en:"Strike"},
  {code:"CAS", fr:"CAS", en:"CAS"},
  {code:"SEAD", fr:"SEAD", en:"SEAD"},
  {code:"ESCORTE", fr:"Escorte", en:"Escort"},
  {code:"INTERCEPTION", fr:"Interception", en:"Interception"},
  {code:"PVP", fr:"PVP", en:"PVP"},
  {code:"AGRESSEUR", fr:"Agresseur", en:"Aggressor"},
  {code:"ENTRAINEMENT", fr:"Entraînement", en:"Training"},
  {code:"PEU_IMPORTE", fr:"Peu importe", en:"Any"}
];
const PREFS_EVENT_TYPES = new Set(["mission","entrainement","campagne"]);

/* v0.26 : type "structuré" -- plateforme fermée (STRUCTURED_GAMES) + map
   DCS uniquement. S'oppose au jeu libre (plateforme libre, pas de map). */
function isStructuredType(tp){ return tp==="mission"||tp==="entrainement"||tp==="campagne"; }

/* Lot 8 : jeu libre -- sélecteur mono-choix (remplace le champ texte libre
   #f-game). Liste figée, ordre exact du brief. "autre" n'est PAS une chaîne
   en dur dans la liste : c'est un sentinel (GAME_OTHER_VALUE) traduit à
   l'affichage via I18N (seul libellé i18n de ce sélecteur), pour ne jamais
   confondre un "autre" saisi par un pilote avec le nom d'un jeu réel lors
   du matching legacy (cf. resolveGameSelection). */
const FREE_PLAY_GAMES = [
  "Arma 3 - SOG Prairie Fire","Star Citizen","Squad 44",
  "Flight Simulator","Cliff of Dover","IL-2 Rise of Flight",
  "Sea of Thieves","Grayzone Warfare","Wolfpack"
];
const GAME_OTHER_VALUE = "__other__";

/* v0.26 : plateforme structurée -- sélecteur mono-choix pour Mission/
   Entraînement/Campagne, liste FERMÉE (pas de sentinel "autre", pas de
   texte libre). Miroir EXACT de la constante Python STRUCTURED_GAMES
   (app/schemas.py). */
const STRUCTURED_GAMES = ["DCS","IL-2 GB","IL-2 Korea"];

/* v0.23 : map -- sélecteur mono-choix pour Mission/Entraînement/Campagne,
   liste FERMÉE (pas de sentinel "autre", contrairement au jeu libre).
   Miroir EXACT (mêmes chaînes, même casse) de la constante Python MAPS
   (app/schemas.py) -- cf. VIGILANCE brief v0.23. Pertinente uniquement
   si la plateforme choisie est "DCS" (v0.26). */
const MAPS = [
  "Syria","Germany (Cold War)","Caucasus","Marianas","Normandy",
  "Afghanistan","Persian Gulf","Sinai","Iraq","Kola",
  "South Atlantic","Nevada","The Channel","Marianas WWII"
];
let mapSelected = null;   // valeur exacte de MAPS, ou null
// État du sélecteur pour la modale actuellement ouverte (re-résolu à
// chaque buildEventFormHTML, cf. plus bas).
let gameSelected = null;   // nom exact dans FREE_PLAY_GAMES, GAME_OTHER_VALUE, ou null
let gameOtherText = "";

function gameLabelDisplay(code){
  return code === GAME_OTHER_VALUE ? t("game_other") : code;
}

/* game_label existant (legacy ou courant) -> état du sélecteur. v0.26 :
   structuré (mission/entraînement/campagne) -> match direct dans
   STRUCTURED_GAMES ou rien (pas de "autre"). jeulibre -> correspond
   exactement à un jeu de la liste -> on le pré-sélectionne ; sinon (valeur
   libre héritée, ou absente) -> "autre" + texte pré-rempli, ou rien. */
function resolveGameSelection(label, type){
  if(isStructuredType(type)){
    return {selected: STRUCTURED_GAMES.includes(label) ? label : null, otherText:""};
  }
  if(!label) return {selected:null, otherText:""};
  if(FREE_PLAY_GAMES.includes(label)) return {selected:label, otherText:""};
  return {selected:GAME_OTHER_VALUE, otherText:label};
}
function missionLabel(code){
  const m = MISSION_TYPES.find(x=>x.code===code);
  if(!m) return code;
  return currentLang==="fr" ? m.fr : m.en;
}

/* Ces SVG utilisent un id="glyph" interne (masque de knockout). Comme les pips
   sont injectés en dizaines d'exemplaires dans le DOM (tableau hebdo, RSVP,
   roster), un id partagé ferait que TOUS les pips affichent le glyphe du
   premier trouvé dans le document. On génère donc un id unique à chaque
   insertion (vigilance DA — ne jamais réutiliser un id="glyph" brut). */
let _pipUid = 0;
function pip(state){
  _pipUid++;
  const uid = "glyph-"+_pipUid;
  return PIP_RAW[state].replace(/id="glyph"/, `id="${uid}"`).replace(/url\(#glyph\)/, `url(#${uid})`);
}

/* ---------- I18N ---------- */
const I18N = {
  fr:{
    signin:"Se connecter avec Discord",
    back:"Retour",
    connected:"Connecté",
    station_planif:"Planification",
    station_debrief:"Escadre",
    station_command:"Centre de Commandement",
    cc_station_sans_role:"Rôle des chefs manquant",
    cc_station_sans_role_toast:"Chef de {squadron} sans le rôle Discord des chefs : demandez-le à un administrateur.",
    status_operational:"Opérationnel",
    open:"Ouvrir",
    debrief_construction_toast:"Module Escadre — l'accès est accordé par un administrateur.",
    adresse_introuvable:"Cette page n'existe plus ou ne vous est pas ouverte.",
    landing_title:"{wing} — Ready Room",
    landing_sub:"Portail interne de l'escadre — planification des vols, présences et debriefing.",
    nav_planche:"La Planche",
    nav_hebdo:"Tableau hebdo",
    theme_dark:"Sombre",
    theme_light:"Greaseboard",
    theme_system:"Système",
    help_btn:"Manuel — cet écran",
    lang_name:"FR",
    month_prev:"Mois précédent",
    month_next:"Mois suivant",
    week_prev:"Semaine précédente",
    week_next:"Semaine suivante",
    view_month:"Mois",
    view_week:"Semaine",
    add_event:"+ Événement",
    filter_all:"Tous",
    type_entrainement:"Entraînement",
    type_mission:"Mission",
    type_campagne:"Campagne",
    type_jeulibre:"Jeu libre",
    today:"Aujourd'hui",
    today_abbr:"Auj.",
    to_answer:"À répondre",
    my_answer:"Ma réponse",
    my_choices:"Mes choix — facultatif",
    agenda_upcoming:"À venir",
    filters_show:"Afficher",
    upcoming_until:"jusqu'au {date}",
    upcoming_none:"Rien de prévu.",
    upcoming_none_todo:"Rien n'attend votre réponse.",
    agenda_all:"Tout le mois",
    agenda_empty_upcoming:"Aucun événement à venir ce mois. Basculez sur « Tout le mois » pour voir l'historique.",
    section_planche:"La Planche",
    section_hebdo:"Tableau de présences hebdo",
    hebdo_current:"Semaine en cours",
    hebdo_next:"Semaine à venir",
    hebdo_empty:"Aucun événement cette semaine.",
    hebdo_no_rsvp:"Aucune inscription cette semaine.",
    hebdo_totals:"Synthèse",
    hebdo_aircraft:"Appareils",
    hebdo_missions:"Missions",
    hebdo_card_empty:"Aucun inscrit",
    rsvp_title:"RSVP",
    rsvp_present:"Présent",
    rsvp_maybe:"Peut-être",
    rsvp_absent:"Absent",
    rsvp_series_label:"↻ Appliquer « {state} » à toute la série",
    rsvp_series_apply:"Appliquer",
    rsvp_series_done:"Appliqué à {n} dates ✓",
    rsvp_series_none:"Aucune date à venir dans la série",
    creator:"Créé par",
    edit:"Modifier",
    delete:"Supprimer",
    close:"Fermer",
    save:"Enregistrer",
    cancel:"Annuler",
    recurring:"Récurrent",
    recurrence_scope:"Cette occurrence / toute la série",
    recurrence_this:"Cette occurrence",
    recurrence_all:"Toute la série",
    roster:"Roster",
    paris_ref:"réf. Europe/Paris",
    new_event_title:"Nouvel événement",
    field_title:"Titre",
    field_type:"Type",
    field_date:"Date",
    field_time:"Heure",
    field_game:"Jeu (si Jeu libre)",
    field_platform:"Plateforme",
    field_map:"Carte",
    field_desc:"Description",
    field_duration:"Durée (min)",
    field_recurring:"Récurrent (hebdomadaire)",
    field_weekdays:"Jours",
    field_interval:"Intervalle (semaines)",
    field_end:"Fin",
    end_none:"Aucune fin",
    end_until:"Jusqu'au",
    end_count:"Nombre d'occurrences",
    edit_event_title:"Modifier l'événement",
    confirm_delete:"Supprimer cet événement ?",
    confirm_delete_seul:"L'événement disparaît de la Planche{rep}.",
    confirm_delete_occ:"Seule l'occurrence du <b>{jour}</b> disparaît{rep}. La série continue.",
    confirm_delete_serie:"<b>Toutes les occurrences de la série</b> disparaissent de la Planche, avec leurs réponses.",
    confirm_rep_un:", avec <b>sa réponse</b>",
    confirm_rep_n:", avec ses <b>{n} réponses</b>",
    serie_eff_titre:"Avant d'enregistrer",
    serie_eff_texte:"Ce changement efface {liste}.",
    serie_eff_rep_un:"<b>1 réponse</b> à venir",
    serie_eff_rep_n:"<b>{n} réponses</b> à venir",
    serie_eff_date_un:"<b>1 date</b> modifiée ou annulée",
    serie_eff_date_n:"<b>{n} dates</b> modifiées ou annulées",
    serie_eff_et:" et ",
    serie_eff_ok:"Effacer et enregistrer",
    evt_modifie:"Cet évènement a été modifié entre-temps : rouvrez-le pour voir la version à jour.",
    nav_plus:"Plus",
    error_generic:"Une erreur est survenue.",
    error_stream_lost:"Connexion perdue — rechargez la page pour vous reconnecter.",
    loading:"Chargement…",
    toast_created:"Événement créé ✓",
    toast_updated:"Événement mis à jour ✓",
    toast_deleted:"Événement supprimé ✓",
    week_of:"Semaine du",
    to:"au",
    no_events:"Aucun événement ce mois-ci.",
    logout:"Déconnexion",
    external_tools_title:"Autres outils {wing}",
    opens_new_tab:"(ouvre un nouvel onglet)",
    manual_tile:"Manuel Pilote",   // Lot « Le Manuel Pilote, le socle » : la tuile de l'accueil
    pref_aircraft_label:"Appareils souhaités",
    pref_missions_label:"Types de mission",
    pref_add:"+ Ajouter",
    pref_filter_ph:"Filtrer…",
    pref_no_match:"Aucun appareil ne correspond.",
    game_other:"autre",
    day_no_events:"Aucun événement ce jour",
    day_create:"+ Créer ce jour",
    new_tag:"NOUVEAU",
    form_group_quoi:"Quoi",
    form_group_quand:"Quand",
    form_group_recurrence:"Récurrence",
    nav_missions:"Missions",
    nav_accueil:"Accueil",
    nav_pilotes:"Dossier",
    nav_campagnes:"Campagnes",
    nav_escadrilles:"Escadrilles",
    // Lot 3.2b — Centre de Commandement, écran Escadrilles
    nav_cc_escadre:"Escadre",
    nav_cc_escadrilles:"Escadrilles",
    nav_cc_membres:"Membres",
    nav_cc_droits:"Droits",
    nav_cc_campagnes:"Campagnes",
    nav_cc_referentiels:"Réf",
    nav_cc_archives:"Arch",
    cc_squadrons_title:"Escadrilles",
    cc_sqn_col_designation:"Identifiant",
    cc_sqn_col_callsign:"Callsign",
    cc_sqn_col_fullname:"Nom complet",
    cc_sqn_aircraft:"Appareils",
    cc_sqn_aircraft_add:"＋ Appareil…",
    cc_sqn_aircraft_other:"Autre…",
    cc_sqn_aircraft_other_ph:"Autre appareil",
    cc_sqn_aircraft_other_ok:"Ajouter",
    cc_sqn_liv_titre:"Livrées",
    cc_sqn_liv_defaut_titre:"Livrée par défaut",
    cc_sqn_liv_tag_custom:"Custom",
    cc_sqn_liv_tag_jeu:"Jeu",
    cc_sqn_liv_nom_ph:"Nom du dossier de la livrée",
    cc_sqn_liv_nom_aria:"Nom de la livrée",
    cc_sqn_liv_jeu_choisir:"Choisir une livrée du jeu…",
    cc_sqn_liv_jeu_aria:"Livrée du jeu",
    cc_sqn_liv_jeu_appareil_aria:"Appareil",
    cc_sqn_liv_retirer:"Retirer",
    cc_sqn_liv_retirer_aria:"Retirer la livrée",
    cc_sqn_liv_ajout_jeu:"+ Livrée du jeu",
    cc_sqn_liv_ajout_custom:"+ Livrée custom",
    cc_sqn_liv_aide:"Une livrée custom s'écrit comme son dossier dans DCS.",
    cc_sqn_liv_aucune:"Aucune livrée.",
    cc_sqn_liv_defaut_aucune:"Aucune",
    cc_sqn_liv_defaut_esc:"Livrées de l'escadrille",
    cc_sqn_liv_defaut_jeu:"Autres livrées du jeu",
    cc_sqn_liv_defaut_aria:"Livrée par défaut {aircraft}",
    cc_sqn_liv_types:"{n} types DCS",
    cc_sqn_liv_sans:"{aircraft} : sans livrée.",
    cc_sqn_liv_sans_appareil:"Déclarez d'abord un appareil.",
    cc_sqn_liv_err_ligne:"Donnez un nom et au moins un appareil à cette livrée.",
    cc_sqn_liv_err_double:"Cette livrée est déjà dans la liste.",
    cc_sqn_liv_res_1:"1 livrée",
    cc_sqn_liv_res_n:"{n} livrées",
    cc_sqn_liv_res_def_1:"1 par défaut",
    cc_sqn_liv_res_def_n:"{n} par défaut",
    cc_sqn_liv_ecartee:"Livrée par défaut {aircraft} écartée : {squadron} l'emporte",
    cc_sqn_nickname:"Surnom",
    cc_sqn_col_status:"Statut",
    cc_sqn_col_role:"Rôle Discord",
    cc_sqn_col_actions:"Actions",
    cc_sqn_status_actif:"Actif",
    cc_sqn_status_sommeil:"Sommeil",
    cc_sqn_empty:"Aucune escadrille enregistrée.",
    cc_sqn_error:"Impossible de charger les escadrilles.",
    cc_sqn_retry:"Réessayer",
    cc_sqn_partial:"Au moins une escadrille active n'a pas de rôle Discord associé — ses membres ne sont pas rattachés automatiquement.",
    deposer:"Déposer",
    deposer_soon:"Dépôt disponible au prochain lot",
    module_soon:"À venir",
    retry:"Réessayer",
    // Lot D2③ — écran Missions
    // Lot 1.5b §10 — cartouche (chassis de feuille), Missions/Session/Vol.
    // Session créée maintenant bien que son écran soit porté au 1.4d.
    cart_title_missions:"MISSIONS",
    cart_sub_missions:"{wing} · Registre des missions volées",
    cart_title_session:"SESSION",
    cart_sub_session:"{wing} · Compte rendu de mission",
    cart_title_flight:"VOL",
    cart_sub_flight:"{wing} · Fiche de vol",
    missions_empty:"Aucune mission déposée",
    missions_no_match:"Aucune mission ne correspond à ces filtres.",
    missions_no_date:"Sans date",
    missions_word:"mission",
    chip_all_squadrons:"Toutes escadrilles",
    chip_all_years:"Tout",
    chip_all_months:"Tous les mois",
    meta_pilots:"pilotes identifiés",
    meta_anon:"anonymes",
    meta_flights:"vols",
    soiree_titre:"Débrief de la soirée",
    soiree_aucune:"Aucune session déposée ce jour-là.",
    soiree_planifiee:"Soirée planifiée",
    meta_kills:"kills",
    acmi_on:"ACMI",
    acmi_off:"Sans ACMI",
    doc_label:"documenté",
    session_error_retry:"Réessayer",
    session_report_cta:"▸ Rapport",
    session_doc_title:"Documentation de la mission",
    session_doc_cap:"des pilotes ont déposé leur débrief",
    session_doc_sources:"Sources",
    session_cov_kind_acmi:"ACMI TacView",
    session_cov_kind_debrief:"débrief",
    session_roster_title:"Roster",
    session_roster_flights_word:"vols",
    session_th_pilot:"Pilote",
    session_th_aircraft:"Appareil",
    session_th_time:"Durée",
    session_th_kills:"Kills",
    session_th_shots:"Tirs",
    session_th_issue:"Issue",
    session_th_data:"Données",
    session_issue_rtb:"RTB",
    session_issue_kia:"KIA",
    session_issue_eject:"Éjection",
    session_issue_none:"—",
    session_badge_reliable:"Débrief déposé",
    session_badge_partial:"Reconstitué",
    session_badge_anon:"Vol anonyme",
    session_member_mark_title:"Membre Ready Room",
    // Correctif finitions §1 — mot court pour .mbr (badge de carte/table),
    // distinct de session_member_mark_title (conservee pour l'infobulle,
    // ou la longueur est un atout).
    session_member_mark_short:"membre",
    session_graveyard_title:"Bilan des destructions",
    session_facts_title:"Faits marquants",
    cart_title_escadre:"ESCADRE",
    cart_sub_escadre:"{wing} · Ordre de bataille",
    escadre_kick:"Ordre de bataille",
    escadre_actives_n:"{n} escadrilles en activité",
    escadre_pilotes_n:"{n} pilotes",
    escadre_pilotes_un:"1 pilote",
    escadre_etat_title:"État civil de l'escadre",
    escadre_designation:"Désignation",
    escadre_nom_complet:"Nom complet",
    escadre_periode:"Période",
    escadre_sim:"Simulateur",
    escadre_actives:"Escadrilles en activité",
    escadre_sommeil:"Escadrilles en sommeil",
    escadre_effectif:"Effectif documenté",
    escadre_orbat_title:"Ordre de bataille",
    escadre_orbat_actives:"En activité",
    escadre_orbat_sommeil:"En sommeil",
    escadre_act_pilotes:"Pilotes actifs",
    escadre_act_heures:"Heures de vol",
    escadre_act_missions:"Missions",
    escadre_act_campagnes:"Campagnes",
    escadre_org_title:"Organigramme de l'escadre",
    escadre_role_leader:"Chef",
    escadre_role_deputy:"Adjoint",
    escadre_free:"Free agents",
    escadre_free_sub:"sans escadrille",
    cart_title_accueil:"POSTE DE COMMANDEMENT",
    cart_sub_accueil:"{wing} · Tableau de bord de l'escadre",
    acc_chiffres_title:"L'escadre en chiffres",
    acc_campagnes_title:"Campagnes en cours",
    acc_aucune_campagne:"Aucune campagne en cours.",
    acc_missions_title:"Dernières missions",
    acc_escadrilles_title:"Escadrilles",
    acc_destructions_title:"Destructions de l'escadre — {n} derniers jours",
    acc_msn:"{n} msn",
    acc_vols:"{n} vols",
    cart_title_escadrille:"ESCADRILLE",
    cart_sub_escadrille:"{wing} · Dossier d'unité",
    cart_title_membre:"FICHE DE SYNTHÈSE",
    cart_sub_membre:"{wing} · Consultable par l'escadre",
    esq_kick:"Dossier d'unité",
    esq_actif:"En activité",
    esq_etat_title:"État civil de l'unité",
    esq_identifiant:"Identifiant",
    esq_nom_complet:"Nom complet",
    esq_callsign:"Callsign",
    esq_escadre:"Escadre",
    esq_dotation:"Dotation",
    esq_effectif:"Effectif actif",
    esq_org_title:"Organigramme",
    esq_act_title:"Activité de l'unité",
    esq_act_missions:"Missions",
    esq_act_heures:"Heures",
    esq_act_sorties:"Sorties",
    esq_act_pilotes:"Pilotes ayant volé",
    mbr_kick:"Membre · {sq}",
    mbr_ancien:"ancien membre",
    mbr_actif:"Actif",
    mbr_archive:"Archivé le {d}",
    mbr_part_title:"Participation",
    mbr_missions:"Missions",
    mbr_temps:"Temps de vol",
    mbr_appareils:"Appareils",
    mbr_depuis:"Depuis",
    mbr_servis_title:"Appareils servis",
    mbr_msn:"{n} msn · {h} h",
    mbr_barrettes_title:"Barrettes de campagne",
    mbr_aucune_barrette:"Aucune campagne volée.",
    mbr_missions_title:"Dernières missions",
    mbr_aucune_mission:"Aucun vol identifié.",
    mbr_error:"La fiche n'a pas pu être chargée.",
    // Lot « L'écran A » : le dossier personnel du pilote connecté (R208, R209, R212).
    cart_title_pilotes:"Dossier personnel",
    cart_sub_pilotes:"{wing} · Réservé au titulaire",
    pil_stamp:"PERSONNEL",
    pil_bilan_title:"Bilan de carrière",
    pil_destr_title:"Destructions par catégorie",
    pil_menaces_title:"Menaces subies",
    pil_carnet_title:"Carnet de vol",
    // Lot « Mission ou training » — la bascule du Dossier
    pil_filtre_label:"Destructions et précision",
    pil_filtre_tout:"Tout",
    pil_filtre_missions:"Missions",
    pil_filtre_training:"Training",
    pil_valid:"Destructions validées",
    pil_air:"Victoires air",
    pil_sol:"Cibles au sol",
    pil_perdus:"Appareils perdus",
    pil_ejections:"Éjections",
    pil_ratio_cap:"destructions par appareil perdu",
    pil_sans_perte:"Sans perte",
    pil_sans_perte_cap:"aucun appareil perdu",
    pil_doc_cap:"Vols documentés par vos dépôts : {f} sur {n}.",
    pil_doc_partiel:"La précision ne porte que sur ceux-là.",
    pil_largages:"{n} largages",
    // Lot « L'efficacité par arme au Dossier » : sous une arme, combien des cibles touchées le pilote a détruites.
    pil_eff_1_1:"{d} détruite sur {n} touchée",
    pil_eff_1_n:"{d} détruite sur {n} touchées",
    pil_eff_n_n:"{d} détruites sur {n} touchées",
    pil_tout:"Tout afficher ({n})",
    pil_voir_f:"Ce que l'escadre voit de vous →",
    cd_mes_cartes:"Mes cartes DCS",
    cd_cartes:"Cartes DCS",
    cd_escadre_titre:"Cartes DCS de l'escadre",
    cd_payantes:"Payantes",
    cd_gratuites:"Gratuites",
    cd_gratuite:"gratuite",
    cd_enregistrer:"Enregistrer",
    cd_modifier:"Modifier",
    cd_replier:"Replier",
    cd_non_declarees:"Pas encore déclarées.",
    cd_aucune:"Aucune carte DCS.",
    cd_declarees:"Déclarées le {date} · {n} carte{s}.",
    cd_pilote:"Pilote",
    cd_non_declare:"non déclaré",
    cd_escadre:"Escadre",
    cd_possedee:"possédée",
    pil_vide:"Votre dossier se remplira à votre premier vol enregistré.",
    pil_prec_vide:"La précision se lit sur les vols documentés par votre propre dépôt.",
    pil_prec_aucun:"Aucun tir enregistré sur vos vols documentés.",
    pil_menaces_vide:"Aucune menace relevée sur vos vols.",
    pil_inconnu:"Inconnu",
    pil_engag_un:"1 engagement",
    pil_engag_n:"{n} engagements",
    pil_vic_un:"1 victoire",
    pil_vic_n:"{n} victoires",
    pil_perte_un:"1 perte",
    pil_perte_n:"{n} pertes",
    pil_dernier:"dernier vol {d}",
    // Lot « L'écran C — la fiche campagne » : le registre et la fiche.
    cart_title_campagnes:"CAMPAGNES",
    cart_sub_campagnes:"{wing} · Registre des campagnes",
    cart_title_campagne:"CAMPAGNE",
    cart_sub_campagne:"{wing} · Dossier de campagne",
    cmp_registre_title:"Registre des campagnes",
    cmp_en_cours:"En cours",
    cmp_closes:"Closes",
    cmp_close:"Close",
    cmp_aucune:"Aucune campagne enregistrée.",
    cmp_kick:"Dossier de campagne",
    cmp_ordre_title:"Ordre d'opérations",
    cmp_theatre:"Théâtre",
    cmp_periode:"Période",
    cmp_periode_en_cours:"{d} → en cours",
    cmp_sim:"Simulateur",
    cmp_sorties:"Sorties",
    cmp_pilotes:"Pilotes",
    cmp_missions_title:"Missions de la campagne",
    cmp_aucune_mission:"Aucune mission rattachée.",
    cmp_participants_title:"Participants",
    cmp_aucun_participant:"Aucun pilote identifié.",
    cmp_bilan_title:"Bilan de campagne — faits d'escadre",
    cmp_introuvable:"Campagne introuvable.",
    cmp_erreur:"Les campagnes n'ont pas pu être chargées.",
    escadre_error:"L'escadre n'a pas pu être chargée.",
    session_mixed_title:"Noms d'arme à vérifier",
    session_mixed_note:"Une même rafale porte plusieurs noms d'arme : deux journaux nomment peut-être la même arme autrement, ou la rafale mêle vraiment deux munitions, comme une bombe et ses sous-munitions. Visible des seuls éditeurs.",
    // Lot 1.4d §6.8/§6.9 — les 3 clés nouvelles du portage DA de l'écran
    // Session, une par note extraite de body_missions.html. Aucune autre
    // clé n'est créée par ce lot.
    // Révision ④.1 — suppression admin d'une session (chgt 4)
    debrief_delete_session_title:"Supprimer la session",
    debrief_toast_session_deleted:"Session supprimée ✓",
    debrief_delete_forbidden:"Réservé aux administrateurs",
    debrief_suppr_titre:"Supprimer cette session ?",
    debrief_suppr_texte:"« {titre} » disparaît du registre, avec {nv} vol{sv}, {nd} fichier{sd} déposé{sd}, les évènements et le récit.",
    slip_detach_titre:"Détacher ce vol ?",
    slip_detach_texte:"Le vol reste sans pilote et le moteur n'y reviendra plus.",
    slip_forget_titre:"Oublier ce nom ?",
    slip_forget_texte:"Les prochains vols sous cet indicatif ne seront plus rattachés automatiquement.",
    recompute_titre:"Recalculer cette session ?",
    recompute_texte:"Tout se recalcule depuis les fichiers déposés. Les corrections manuelles d'identité sont conservées.",
    recompute_go:"Recalculer",
    recompute_all_titre:"Recalculer les sessions périmées ?",
    recompute_all_texte:"{n} session{s} à recalculer depuis leurs fichiers. L'opération peut durer plusieurs minutes.",
    recompute_all_go:"Tout recalculer",
    debrief_delete_redaction:"Une rédaction est en cours sur cette mission : réessayez quand elle sera finie.",
    // Lot D2③ — modale Déposer
    deposer_modal_type:"Alimenter le débrief",
    deposer_modal_title:"Déposer des fichiers",
    deposer_dz_big:"Glissez un ACMI ou un débrief.log",
    deposer_dz_sub:".acmi (TacView) · debrief.log — ou cliquez pour parcourir",
    deposer_dz_big_touch:"Touchez pour choisir vos fichiers",
    deposer_dz_sub_touch:".acmi (TacView) · debrief.log",
    deposer_depositor_label:"Qui dépose ce débrief ?",
    deposer_depositor_note:"Un débrief ne contient pas d'identité fiable : vous devez déclarer le pilote. La mission est rattachée automatiquement (aucun choix à faire).",
    deposer_me:"moi",
    kind_debrief:"débrief.log (client DCS)",
    kind_acmi:"ACMI TacView",
    deposer_remove_file:"Retirer",
    deposer_in_progress:"Dépôt en cours…",
    deposer_submit:"Déposer",
    deposer_again:"Déposer d'autres fichiers",
    deposer_noop:"Déjà déposé — aucun changement",
    deposer_attached_to:"Rattaché à",
    deposer_n_uploads:"Apports (fichiers)",
    deposer_n_flights:"Vols",
    deposer_n_kills:"Kills",
    // Lot D2⑤ — écran Vol (détail par vie)
    flight_stat_kills:"Kills",
    flight_stat_time:"Durée",
    // Lot « Les heures de jour et de nuit » (v1.0068).
    jn_de_jour:"de jour",
    jn_de_nuit:"de nuit",
    flight_periode_jour:"Vol de jour",
    flight_periode_nuit:"Vol de nuit",
    flight_periode_corrigee:"corrigé",
    flight_periode_corriger:"Corriger : {p}",
    flight_periode_fail:"La correction n'a pas abouti.",
    flight_stat_altmax:"Alt. max",
    flight_stat_bilan:"Bilan (K−D)",
    flight_summary_title:"Synthèse du vol",
    flight_timeline_title:"Journal du vol",
    flight_timeline_empty:"Aucun événement horodaté pour ce vol.",
    flight_tag_phase:"phase",
    flight_tag_kill:"kill",
    flight_tag_threat:"menace",
    flight_tag_shot:"tir",
    flight_tag_collab:"collaboration",
    flight_tag_destruction:"destruction",
    // Lot « Le journal dit quand un tir touche » : la cible touchée qui survit,
    // et la destruction par l'explosion d'une épave.
    flight_tag_touche:"touché",
    flight_tag_collateral:"collatéral",
    flight_phase_takeoff:"Décollage",
    // Réservée (R137) : le moteur replie les sauts, le front ne les montre
    // plus depuis le v0.9992. Gardée pour le jour où il les montrera.
    flight_phase_saut:"Saut",
    flight_phase_land:"Atterrissage",
    flight_phase_crash:"Crash",
    flight_phase_eject:"Éjection",
    flight_phase_pilot_dead:"Mort du pilote",
    flight_phase_engine_startup:"Mise en route moteur",
    flight_phase_engine_shutdown:"Coupure moteur",
    flight_precision_title:"Précision par arme",
    flight_precision_empty:"Aucun tir enregistré pour ce vol.",
    flight_releases_word:"largages",
    flight_releases_tag:"largages",
    // Lot « L'écran de la précision » : les types d'armes, et ce que comptent les nombres.
    prec_cat_missiles:"Missiles",
    prec_cat_roquettes:"Roquettes",
    prec_cat_bombes:"Bombes",
    prec_cat_sousmun:"Sous-munitions",
    prec_cat_canon:"Canon",
    prec_cat_autres:"Autres",
    prec_larg_1:"{n} conteneur largué",
    prec_larg_n:"{n} conteneurs largués",
    prec_salve_1:"en {n} salve",
    prec_salve_n:"en {n} salves",
    prec_roq_1:"{n} roquette tirée",
    prec_roq_n:"{n} roquettes tirées",
    prec_obus_1:"{n} obus",
    prec_obus_n:"{n} obus",
    prec_raf_1:"en {n} rafale",
    prec_raf_n:"en {n} rafales",
    prec_rafbut_1:"{n} rafale au but",
    prec_rafbut_n:"{n} rafales au but",
    flight_threats_title:"Menaces subies",
    flight_threats_none_note:"Aucun impact subi. Les tirs non guidés sans cible déclarée restent invisibles (limite des données DCS).",
    flight_kills_title:"Bilan des destructions",
    flight_kills_frat_un:"tir fratricide, hors bilan",
    flight_kills_frat:"tirs fratricides, hors bilan",
    flight_threats_empty:"Aucune menace enregistrée pour ce vol.",
    flight_grav_aimed:"Visé",
    flight_grav_hit:"Touché",
    flight_grav_down:"Abattu",
    // Lot 1.5 — tampon "Incomplet" (§2.3 du brief)
    flight_stamp_incomplete:"Incomplet",
    // Lot D2⑤ — modale Rapport de mission
    report_modal_title:"Rapport de mission",
    // Lot 1.6 §5.1 (R-A) — libellé d'imprimé constant
    report_form_number:"IMPRIMÉ 4V-12 · RAPPORT",
    report_toggle_narrative:"Récit",
    report_toggle_raw:"Brut horodaté",
    report_note:"Récit rédigé par un modèle de langage à partir des faits assemblés par le serveur (aucun chiffre n'est jamais inventé).",
    report_empty:"Pas encore assez de données pour générer un rapport.",
    // Lot R2 §5 — rédaction du Récit par un modèle de langage, figée en base
    report_generate_btn:"Rédiger",
    report_regenerate_btn:"Réécrire",
    report_generating:"Rédaction en cours…",
    report_stamp_a_corriger:"À corriger",
    report_loading:"Chargement du rapport…",
    report_not_generated:"Aucun récit rédigé pour l'instant.",
    // Lot FR source unique §2⑤ — mention affichée en EN quand seule la
    // traduction manque (le français, lui, existe déjà)
    report_translation_pending:"Traduction en cours…",
    report_translation_unavailable:"Traduction indisponible.",
    report_gen_error_generic:"La rédaction a échoué. Réessayez plus tard.",
    // Lot « Polish du moteur du Débrief » : refus de plafond (429) de la rédaction
    report_cap_reached:"Plafond de générations atteint pour cette session (temporaire : il se libère au fil de l'heure écoulée, réessayez plus tard).",
    // Lot R6 §6 — état "en cours", porté par la lecture, jamais par le canal
    report_busy_by:"Rédaction en cours par {name}…",
    report_busy_conflict:"Une rédaction est déjà en cours sur cette session.",
    report_stale_blocked:"Les statistiques de cette session sont à recalculer : la rédaction attend le recalcul.",
    // Lot 2.1 — nommage des missions et note pour l'escadre
    deposer_mission_name_label:"Nom de la mission",
    deposer_wing_note_label:"Note pour l'escadre",
    deposer_mission_name_hint:"Le nom ne s'applique que si la mission n'en a pas déjà un.",
    deposer_mission_created:"Nouvelle mission créée",
    deposer_mission_joined:"Rattachée à une mission existante",
    deposer_name_applied:"Nom retenu",
    deposer_name_already_set:"Nom déjà défini",
    deposer_note_applied:"Note retenue",
    deposer_note_already_set:"Note déjà définie",
    // Lot 2.3 — la campagne en entité
    deposer_campaign_label:"Campagne",
    campaign_none_option:"Aucune",
    deposer_campaign_conflict:"La session est déjà rattachée à une autre campagne : le choix n'a pas été appliqué.",
    session_edit_campaign_label:"Campagne",
    // Lot « Mission ou training » — la nature d'une session
    nature_label:"Nature",
    nature_mission:"Mission",
    nature_training:"Training",
    nature_stamp:"Training",
    nature_stamp_sub:"EXERCICE · EXERCICE",
    deposer_nature_label:"Nature de la session",
    error_field_too_long:"Ce champ dépasse la longueur autorisée.",
    session_edit_cta:"Modifier",
    session_edit_name_label:"Nom de la mission",
    session_edit_note_label:"Note pour l'escadre",
    session_edit_save:"Enregistrer",
    session_edit_cancel:"Annuler",
    session_edit_saved:"Modifications enregistrées ✓",
    recompute_cta:"Recalc.",
    recompute_running:"Recalcul en cours…",
    recompute_done:"Session recalculée ✓",
    recompute_error:"Échec du recalcul.",
    // Lot Fraîcheur v0.9939 (brief §9) : quatre clés neuves.
    stale_mark:"à recalculer",
    recompute_all_cta:"Recalculer {n} session{s}",
    recompute_all_toast:"{n} session(s) recalculée(s) ✓",
    // Lot « Le rattachement des dépôts » (v1.0052) : la marque, la provenance, le déplacement, la fusion.
    verif_mark:"À vérifier",
    verif_mark_title:"Un fichier y est rattaché sur l'en-tête d'une mission d'exemple de DCS",
    src_move_cta:"Déplacer…",
    src_prov_titre:"rattaché par son titre",
    src_prov_contenu:"rattaché par son contenu — l'en-tête nommait « {t} »",
    src_prov_manuel:"déplacé à la main par {nom}",
    src_prov_exemple:"rattaché par son titre — en-tête d'une mission d'exemple de DCS",
    src_move_title_debrief:"Déplacer le débrief de {dep} vers…",
    src_move_title_acmi:"Déplacer l'ACMI de {dep} vers…",
    src_move_files:"{n} fichier{s}",
    src_move_new:"Une nouvelle mission",
    src_move_none:"Aucune autre mission à trois jours près.",
    src_move_note:"Les deux missions sont recalculées. Une mission vidée de ses fichiers disparaît.",
    src_move_go:"Déplacer",
    src_move_done:"Fichier déplacé ✓",
    merge_label:"Fusionner avec une autre mission",
    merge_none:"— aucune —",
    merge_cta:"Fusionner…",
    merge_confirm:"« {t} » sera fondue dans cette mission : ses {n} fichier{s} la rejoignent, puis elle disparaît avec son nom, sa note et son récit. Cette mission garde les siens.",
    merge_confirm_un:"« {t} » sera fondue dans cette mission : son fichier la rejoint, puis elle disparaît avec son nom, sa note et son récit. Cette mission garde les siens.",
    merge_go:"Fusionner",
    merge_done:"Missions fusionnées ✓",
    session_wing_note_label:"Note escadre :",
    cc_members_title:"Membres",
    cc_mbr_col_member:"Membre",
    cc_mbr_col_rank:"Rang",
    cc_mbr_col_admin:"Administrateur",
    cc_mbr_col_seen:"Dernière connexion",
    cc_mbr_rank_leader:"Chef d'escadrille",
    cc_mbr_rank_deputy:"Adjoint",
    cc_mbr_rank_member:"Membre",
    cc_mbr_admin_yes:"Administrateur",
    cc_mbr_empty:"Aucun membre enregistré.",
    cc_mbr_error:"Impossible de charger les membres.",
    cc_mbr_retry:"Réessayer",
    cc_appel_last:"Dernier appel",
    cc_appel_btn:"Faire l'appel",
    cc_appel_running:"Appel en cours…",
    cc_appel_none:"Aucun changement.",
    cc_appel_and:"et",
    cc_appel_out_one:"{names} sort de l'effectif",
    cc_appel_out_n:"{names} sortent de l'effectif",
    cc_appel_move_one:"{names} passe au {sq}",
    cc_appel_move_n:"{names} passent au {sq}",
    cc_appel_fa_one:"{names} passe Free Agent",
    cc_appel_fa_n:"{names} passent Free Agents",
    cc_appel_back_one:"{names} revient dans l'effectif",
    cc_appel_back_n:"{names} reviennent dans l'effectif",
    cc_appel_in_one:"{names} arrive au {sq}",
    cc_appel_in_n:"{names} arrivent au {sq}",
    cc_appel_in_fa_one:"{names} arrive en Free Agent",
    cc_appel_in_fa_n:"{names} arrivent en Free Agents",
    cc_appel_list_ko:"serveur non listé ({reason}) : personne n'a pu entrer",
    cc_appel_error:"Appel interrompu — {reason}. Rien n'a été écrit.",
    // Lot « Le Centre au doigt et à la charte » (v1.0081).
    cc_mbr_search_ph:"Chercher un membre",
    cc_mbr_count:"{n} membre{s}",
    cc_relances_n:"{n} pilote{s} en retard",
    cc_sqn_sleep_titre:"Endormir cette escadrille ?",
    cc_sqn_wake_titre:"Réveiller cette escadrille ?",
    cc_sqn_crest_titre:"Poser cet écusson ?",
    cc_rights_role_titre:"Changer le rôle des chefs ?",
    cc_rights_chef_titre:"Nommer le chef d'escadrille ?",
    cc_rights_chef_none_titre:"Retirer le chef d'escadrille ?",
    cc_rights_conn_titre:"Retirer ce rôle de la connexion ?",
    cc_camp_delete_titre:"Supprimer cette campagne ?",
    cc_esc_titre:"Modifier l'escadre ?",
    cc_esc_emblem_titre:"Poser cet emblème ?",
    cc_ref_import_titre:"Importer ce fichier ?",
    // Lot « Les relances » (R8) : la liste de l'écran Membres.
    cc_relances_title:"Relances de planning",
    cc_relances_none:"Aucun pilote en retard.",
    cc_relances_last:"dernière réponse le {date}",
    cc_relances_never:"aucune réponse",
    cc_relances_dest:"Destinataires : {names}",
    cc_relances_dest_none:"Aucun destinataire (écran Droits) : aucun MP ne part.",
    cc_relances_refus:"MP refusé par {name} le {date}",
    cc_rights_title:"Droits",
    cc_rights_role_title:"Rôle Discord « chef d'escadrille »",
    cc_rights_role_hint:"Un seul rôle pour toute l'escadre, choisi dans la liste des rôles du serveur Discord — aucun identifiant à saisir. Tant qu'il n'est pas renseigné, seuls les administrateurs et les adjoints entrent dans le module, et aucun chef ne peut être désigné ci-dessous.",
    cc_rights_role_src:"lu sur le serveur Discord",
    cc_rights_role_none:"aucun",
    cc_rights_role_absent:"absent du serveur",
    cc_rights_cmd_title:"Commandement des escadrilles",
    cc_rights_cmd_hint_admin:"Le chef est désigné par vous, parmi les membres de l'escadrille qui portent le rôle ci-dessus, relevé à chaque connexion et à chaque appel. Un membre à qui le rôle vient d'être attribué sur Discord apparaît après l'appel suivant ou sa prochaine connexion. L'adjoint est désigné par vous ou par le chef de l'escadrille.",
    cc_rights_cmd_hint_chef:"Vous désignez l'adjoint de votre escadrille. Le reste est du ressort d'un administrateur.",
    cc_rights_col_squadron:"Escadrille",
    cc_rights_col_chef:"Chef",
    cc_rights_col_deputy:"Adjoint",
    cc_rights_no_candidate:"aucun membre de cette escadrille ne porte ce rôle au dernier relevé",
    cc_rights_pick_role_first:"choisissez d'abord le rôle ci-dessus",
    cc_rights_no_member:"aucun membre",
    cc_rights_plan_title:"Édition des événements du planning",
    cc_rights_plan_hint:"Qui peut créer des événements. Par rôle du serveur Discord, ou personne par personne. <b>Chacun modifie ensuite ce qu'il a créé</b> — modifier l'événement d'un autre est un droit distinct, plus bas.",
    cc_rights_plan_by_role:"Par rôle Discord",
    cc_rights_plan_by_person:"Nominativement",
    cc_rights_plan_none:"Aucun",
    cc_rights_add:"Ajouter",
    cc_rights_cancel:"Annuler",
    cc_rights_chip_remove:"Retirer",
    cc_rights_choose:"choisir",
    cc_rights_conn_title:"Accès à l'application",
    cc_rights_conn_hint:"Les rôles Discord qui ouvrent la connexion. Un membre qui n'en porte aucun ne peut pas entrer. Les administrateurs entrent toujours, quels que soient leurs rôles.",
    cc_rights_conn_effect:"Un retrait prend effet immédiatement : la personne retombe sur la page de garde à son geste suivant. Le remettre la fait rentrer aussitôt.",
    cc_rights_conn_src_app:"Géré ici.",
    cc_rights_debrief_title:"Accès au module Escadre",
    cc_rights_debrief_hint:"Les porteurs de ces rôles entrent dans le module Escadre, en plus des administrateurs, qui y entrent toujours.",
    cc_rights_debrief_reload_hint:"Un octroi ne prend effet qu'au rechargement de la page — pas immédiatement, à la différence de l'accès à l'application.",
    // Lot « Les relances » (R7) : le réglage, à l'écran Droits.
    cc_rights_relances_title:"Relances de planning",
    cc_rights_relances_hint:"Les porteurs de ces rôles et ces comptes reçoivent un MP Discord quand un pilote d'escadrille n'a répondu à aucune occurrence du planning, ni des quatre dernières semaines ni des 90 jours à venir — une fois, quand son nom s'ajoute. Un destinataire ajouté reçoit aussitôt la liste en cours. Sans destinataire, aucun MP ne part ; la liste reste à l'écran Membres.",
    // Lot « Les relances nominatives » (R1) : la rangée des comptes.
    cc_rights_relances_ids:"Comptes",
    cc_rights_conn_qual_chef:"désigne les chefs",
    cc_rights_conn_qual_squadron:"rattache à {squadron}",
    cc_rights_conn_add:"Ajouter un rôle qui ouvre la connexion",
    cc_rights_conn_confirm:"Retirer <b>{role}</b> de l'accès ?",
    cc_rights_conn_confirm_impact_one:" <b>{n} membre connu</b> perdrait son dernier rôle d'accès et ne pourrait plus entrer.",
    cc_rights_conn_confirm_impact_many:" <b>{n} membres connus</b> perdraient leur dernier rôle d'accès et ne pourraient plus entrer.",
    cc_rights_conn_confirm_mine:" <b>Votre accès d'administrateur reste ouvert, quel que soit ce retrait.</b>",
    cc_rights_conn_immediate:" L'effet est <b>immédiat</b>.",
    cc_rights_conn_deny_last:"Impossible de retirer <b>{role}</b> : la liste ne peut pas être vidée. Ajoutez un autre rôle d'abord.",
    cc_rights_conn_ko:"serveur Discord injoignable — ajout impossible",
    cc_rights_content_title:"Droits sur le contenu",
    cc_rights_content_hint:"Quatre droits qui s'accordent par rôle Discord. Les administrateurs les ont toujours.",
    cc_rights_content_sess_title:"Renommer une mission et écrire la note d'escadre",
    cc_rights_content_sess_hint:"Portée globale : les sessions sont multi-escadrilles.",
    cc_rights_content_evt_title:"Modifier l'événement de quelqu'un d'autre",
    cc_rights_content_evt_hint:"S'ajoute à l'édition du planning ci-dessus, qui ne permet de corriger que ses propres événements.",
    cc_rights_content_evt_reload_hint:"Un octroi ne prend effet qu'au rechargement de la page — pas immédiatement, à la différence de l'accès à l'application.",
    cc_rights_content_camp_title:"Créer et modifier une campagne",
    cc_rights_content_camp_hint:"Même droit pour les deux gestes : c'est le même métier sur le même objet.",
    cc_rights_content_campdel_title:"Supprimer une campagne",
    cc_rights_content_campdel_hint:"Droit distinct, volontairement. Une campagne à laquelle des missions sont rattachées ne peut pas être supprimée, quel que soit le porteur.",
    cc_rights_content_camp_reload_hint:"Pour ces deux droits aussi, un octroi ne prend effet qu'au rechargement de la page.",
    cc_rights_ref_title:"Les rôles Discord, et ce qu'ils font ici",
    cc_rights_ref_hint:"Référence de lecture, pour tenir les rôles à jour côté Discord. Chaque membre porte un rôle qui ouvre l'accès ; les rôles d'escadrille et le rôle des chefs sont des rôles distincts, et n'ont pas à figurer dans la liste d'accès.",
    cc_rights_ref_col_role:"Rôle Discord",
    cc_rights_ref_col_office:"Ce qu'il fait ici",
    cc_rights_ref_col_count:"Membres connus",
    cc_rights_ref_limit_hint:"Le décompte porte sur les membres <b>connus de la Ready Room</b>, d'après les rôles relevés à leur connexion et à chaque appel.",
    cc_rights_ref_office_none:"—",
    cc_rights_ref_office_access:"Ouvre l'accès",
    cc_rights_ref_office_plan:"Édite le planning",
    cc_rights_ref_office_session:"Renomme les missions",
    cc_rights_ref_office_event_any:"Modifie les événements d'autrui",
    cc_rights_ref_office_campaign:"Crée et modifie les campagnes",
    cc_rights_ref_office_campaign_delete:"Supprime les campagnes",
    cc_rights_ref_office_debrief:"Entre dans l'Escadre",
    cc_rights_ref_absent_note:"Rôle(s) référencé(s) ici mais absent(s) du serveur Discord : {roles}.",
    cc_rights_partial:"Sans chef désigné : {squadrons}. Les membres de ces escadrilles n'ont personne pour les administrer.",
    cc_rights_chef_sans_role_opt:"{name} · sans le rôle des chefs",
    cc_rights_chef_sans_role:"sans le rôle des chefs",
    cc_rights_partial_sans_role:"Chefs sans le rôle Discord des chefs, qui n'entrent donc pas au Centre : {squadrons}.",
    cc_rights_deputy_note:"Votre rang : adjoint de {squadron}. Le chef et l'adjoint d'une escadrille sont désignés ici par un administrateur ; l'adjoint peut aussi l'être par le chef.",
    cc_rights_no_squadron:"Vous ne commandez aucune escadrille. Les chefs et les adjoints sont désignés à cet écran par un administrateur.",
    cc_rights_empty:"Aucune escadrille active.",
    cc_rights_error:"Impossible de charger les droits.",
    cc_rights_retry:"Réessayer",
    cc_rights_confirm_chef:"Désigner {name} chef de {squadron} ?",
    cc_rights_confirm_chef_takeover:"Désigner {name} chef de {squadron} ? {previous} redevient simple membre.",
    cc_rights_confirm_chef_none:"Retirer {previous} du commandement de {squadron} ? L'escadrille n'aura plus de chef.",
    cc_rights_confirm_role:"Confirmer le rôle Discord des chefs d'escadrille : {role} ?",
    cc_rights_deny_last_editor:"Retrait refusé — dernier éditeur du planning. Ajoutez-en un autre d'abord.",
    cc_rights_confirm_apply:"Appliquer",
    cc_sqn_act_edit:"Modifier",
    cc_sqn_act_save:"Enregistrer",
    cc_sqn_act_sleep:"Endormir",
    cc_sqn_act_wake:"Réveiller",
    cc_sqn_rename_effect:"Le nouveau nom {new} remplacera {old} partout dans l'application, y compris sur le planning hebdomadaire.",
    cc_sqn_tag_effect:"{old} ne sera plus retiré des pseudos — {new} le sera à sa place. Les noms affichés changent pour toutes les escadrilles, pas seulement celle-ci.",
    cc_sqn_sleep_confirm:"Mettre {squadron} en sommeil ? Son rôle Discord cesse d'être reconnu. Au prochain appel ou à leur prochaine connexion, ses {count} membres la quittent : Free Agents s'ils gardent l'accès à l'application, archivés sinon.",
    cc_sqn_sleep_confirm_empty:"Mettre {squadron} en sommeil ? Elle ne rattache aucun membre ; son rôle Discord cesse d'être reconnu.",
    cc_sqn_wake_pick:"Réveiller {squadron} : choisissez le rôle Discord qui rattachera désormais ses membres.",
    cc_sqn_wake_deny:"Choisissez d'abord le rôle Discord qui rattachera les membres — sans lui, {squadron} serait active et ne rattacherait personne.",
    cc_sqn_create_title:"Créer une escadrille",
    cc_sqn_create_hint:"L'identifiant est retiré des pseudos des membres partout dans l'application — saisissez-le exactement tel qu'il apparaît dans leurs noms Discord.",
    cc_sqn_create_submit:"Créer",
    cc_sqn_create_deny_fields:"Une escadrille a besoin d'un identifiant.",
    cc_sqn_create_deny_role:"Ce rôle Discord rattache déjà {squadron}. Deux escadrilles actives ne peuvent pas partager un rôle.",
    cc_sqn_created:"{squadron} est créée. Elle rattachera ses membres à l'appel suivant ou à leur prochaine connexion.",
    cc_sqn_act_crest:"Écusson…",
    cc_sqn_crest_alt:"Écusson de {squadron}",
    cc_sqn_crest_none:"Aucun écusson",
    cc_sqn_crest_preview:"{dims} → mis au carré, réduit à 512 px au maximum, ré-encodé en PNG.",
    cc_sqn_crest_apply:"Poser l'écusson",
    cc_sqn_crest_done:"L'écusson de {squadron} est posé.",
    cc_sqn_crest_deny_vector:"{name} est un fichier vectoriel : il peut embarquer du code exécutable. PNG ou WebP uniquement, jamais de vectoriel.",
    cc_sqn_crest_deny_weight:"{name} pèse {size} Mo. 2 Mio au maximum — un écusson est un aplat, pas une photographie.",
    cc_sqn_crest_deny_format:"{name} n'est pas une image PNG ou WebP. L'extension ne fait pas foi : le serveur relit les premiers octets du fichier.",
    cc_sqn_crest_deny_broken:"{name} est illisible ou tronqué.",
    cc_campaigns_title:"Campagnes",
    cc_camp_col_name:"Campagne",
    cc_camp_col_sim:"Simulateur",
    cc_camp_col_theater:"Théâtre",
    cc_camp_col_status:"Statut",
    cc_camp_col_missions:"Missions",
    cc_camp_col_actions:"Actions",
    cc_camp_field_name_ph:"Nom de la campagne",
    cc_camp_field_desc:"Description",
    cc_camp_status_en_cours:"En cours",
    cc_camp_status_close:"Close",
    cc_camp_empty:"Aucune campagne enregistrée. Une mission déposée sans campagne reste une mission normale — le rattachement est facultatif.",
    cc_camp_error:"Impossible de charger les campagnes.",
    cc_camp_retry:"Réessayer",
    cc_escadre_title:"Escadre",
    cc_esc_emblem_btn:"Emblème…",
    cc_esc_emblem_alt:"Emblème de {wing}",
    cc_esc_emblem_apply:"Poser l'emblème",
    cc_esc_emblem_done:"L'emblème est posé.",
    cc_esc_id_title:"Identité de l'escadre",
    cc_esc_id_hint:"Ce qui s'écrit ici remplace l'escadre partout dans l'application : sous-titres des écrans, barre haute, page de connexion, messages Discord, références de classement.",
    cc_esc_admin_only:"Réservé aux administrateurs.",
    cc_esc_f_designation:"Désignation",
    cc_esc_f_fullname:"Nom complet",
    cc_esc_f_period:"Période",
    cc_esc_f_sigle:"Sigle",
    cc_esc_f_tag:"Tag",
    cc_esc_h_period:"Une seule langue : elle s'affiche telle quelle en français comme en anglais.",
    cc_esc_h_sigle:"Dans les références de classement : « NATO RESTRICTED · {sigle}/DCS/MSN/0012 ».",
    cc_esc_h_tag:"Le préfixe retiré en tête des pseudos : « {tag} | Kodiak » s'affiche « Kodiak ». Il suit la désignation.",
    cc_esc_save:"Enregistrer",
    cc_esc_confirm:"Changements : {changes}.",
    cc_esc_change_item:"{field} « {from} » → « {to} »",
    cc_esc_confirm_tag:"Le tag change : rien de ce qui est enregistré n'est réécrit, mais un pseudo Discord qui commence encore par « {old} » gardera ce préfixe — au planning, dans les messages Discord et les relances — tant que le pilote ne l'aura pas changé.",
    cc_esc_saved:"L'identité de l'escadre est enregistrée.",
    cc_esc_error:"Impossible de charger l'identité de l'escadre.",
    cc_ref_title:"Référentiels",
    cc_ref_hint:"Les noms que DCS donne aux unités et aux armes, et le nom que la Ready Room affiche à leur place — au journal d'un vol, dans les bilans, la précision, les menaces et le Dossier. Une clé sans libellé s'affiche telle quelle. La catégorie d'un type range ses destructions dans les bilans ; elle est automatique, sauf si elle est forcée ici.",
    cc_ref_search_ph:"Chercher une clé ou un libellé",
    cc_ref_sans_libelle:"Sans libellé ({n})",
    cc_ref_export:"Exporter",
    cc_ref_import:"Importer…",
    cc_ref_types_title:"Types d'unités · {n}",
    cc_ref_armes_title:"Armes · {n}",
    cc_ref_col_cle:"Clé DCS",
    cc_ref_col_libelle:"Libellé",
    cc_ref_col_categorie:"Catégorie",
    cc_ref_modifier:"Modifier",
    cc_ref_cle_affichee:"— clé affichée",
    cc_ref_forcee:"forcée",
    cc_ref_auto:"Automatique ({cat})",
    // Lot « La plume » §6 : les catégories de cible, dans la langue de l'écran (catLabel).
    cat_avion:"Avion",
    cat_helicoptere:"Hélicoptère",
    cat_defense_aa:"Défense AA",
    cat_char:"Char",
    cat_artillerie:"Artillerie",
    cat_blinde_leger:"Blindé léger",
    cat_infanterie:"Infanterie",
    cat_vehicule:"Véhicule",
    cat_navire:"Navire",
    cat_static:"Static",
    cat_inconnu:"Inconnu",
    cc_ref_import_bilan:"{fichier} — contrat {contrat}, version {version}. Types : {tp} libellés posés, {ti} inchangés, {tc} catégories forcées. Armes : {ap} libellés posés, {ai} inchangés. {r} refusé(s). Rien n'est supprimé : une clé absente du fichier garde son libellé.",
    cc_ref_refus_item:"« {cle} » : {raison}",
    cc_ref_import_invalide:"{fichier} n'est pas un référentiel lisible : {raison}",
    cc_ref_import_done:"Le référentiel est importé.",
    cc_ref_saved:"« {cle} » est enregistré.",
    cc_ref_error:"Impossible de charger les référentiels.",
    cc_ref_empty_filter:"Aucune clé ne correspond.",
    // Lot « L'écran Archives du Centre » : 25 clés (écran Archives du Centre de Commandement).
    cc_arch_title:"Archives",
    cc_arch_mbr_title:"Membres archivés",
    cc_arch_mbr_hint:"Les profils sortis de l'effectif à l'appel. Rien n'est effacé : leurs vols et leurs missions restent, et un retour sur Discord les réintègre au prochain appel.",
    cc_arch_col_membre:"Membre",
    cc_arch_col_escadrille:"Dernière escadrille",
    cc_arch_col_sortie:"Sortie",
    cc_arch_col_missions:"Missions",
    cc_arch_col_heures:"Heures",
    cc_arch_mbr_empty:"Aucun membre archivé.",
    cc_arch_sav_title:"Sauvegardes",
    cc_arch_sav_hint:"Une sauvegarde prend la base et les écussons ; les fichiers déposés dans l'Escadre restent à la sauvegarde de la machine. Les dix dernières manuelles sont gardées ; les automatiques suivent leur réglage, celles du déploiement leur propre purge. La restauration se fait en ligne de commande (guide d'installation, chapitre 11), jamais d'ici.",
    cc_arch_sav_btn:"Sauvegarder maintenant",
    cc_arch_sav_busy:"Sauvegarde en cours…",
    cc_arch_sav_done:"Sauvegarde faite : {taille}, base et écussons.",
    cc_arch_col_date:"Date",
    cc_arch_col_origine:"Origine",
    cc_arch_col_revision:"Révision",
    cc_arch_col_taille:"Taille",
    cc_arch_col_fichiers:"Fichiers",
    cc_arch_origine_manuelle:"Manuelle",
    cc_arch_origine_deploiement:"Déploiement",
    // Lot « Le Centre côté serveur » : la sauvegarde d'`entrypoint.sh`, avant une migration.
    cc_arch_origine_migration:"Migration",
    // Lot « Les sauvegardes automatiques » : l'origine, le panneau de réglage, son état.
    cc_arch_origine_automatique:"Automatique",
    cc_arch_auto_title:"Sauvegarde automatique",
    cc_arch_auto_freq_0:"Désactivée",
    cc_arch_auto_freq_h:"Toutes les {n} h",
    cc_arch_auto_freq_168:"Tous les 7 jours",
    cc_arch_auto_garder:"Garder les {n} dernières",
    cc_arch_auto_derniere:"Dernière : {date} · {heure}",
    cc_arch_auto_aucune:"Aucune pour l'instant",
    cc_arch_auto_echec:"Échec de la dernière tentative ({date} · {heure}) : {raison}",
    cc_arch_auto_aria_freq:"Fréquence",
    cc_arch_auto_aria_garder:"Rétention",
    cc_arch_dl_base:"Base",
    cc_arch_dl_ecussons:"Écussons",
    cc_arch_sav_empty:"Aucune sauvegarde.",
    cc_arch_error:"Impossible de charger les archives.",
    // Lot « Polish du Centre » : le diagnostic d'accès (écran Membres) et le journal des modifications (écran Archives) — 88 clés.
    cc_diag_title:"Diagnostic d'accès",
    cc_diag_hint:"Pour un membre : chaque droit, s'il l'a, et ce qui le lui ouvre. Réservé aux administrateurs.",
    cc_diag_choose:"Choisir un membre…",
    cc_diag_roles:"Rôles Discord relevés au dernier appel ou à la dernière connexion : {roles}",
    cc_diag_roles_none:"aucun",
    cc_diag_col_droit:"Droit",
    cc_diag_col_accorde:"Accordé",
    cc_diag_col_par:"Par",
    cc_diag_oui:"Oui",
    cc_diag_non:"Non",
    cc_diag_error:"Impossible de lire les accès de ce membre.",
    cc_diag_d_app_access:"Connexion à l'application",
    cc_diag_d_command_access:"Centre de Commandement",
    cc_diag_d_debrief_access:"Escadre",
    cc_diag_d_event_create:"Planning — créer",
    cc_diag_d_event_edit_any:"Planning — modifier tout",
    cc_diag_d_session_edit:"Missions — modifier",
    cc_diag_d_campaign_manage:"Campagnes — gérer",
    cc_diag_d_campaign_delete:"Campagnes — supprimer",
    cc_diag_d_relances_destinataire:"Relances — recevoir",
    cc_diag_s_admin:"administrateur (.env)",
    cc_diag_s_role:"rôle « {role} »",
    cc_diag_s_compte:"nommément, écran Droits",
    cc_diag_s_adjoint:"adjoint du {escadrille}",
    cc_diag_s_aucun:"aucun de ses rôles, ni son compte",
    // Lot « La connexion de secours » : le lien de connexion de secours (écran Membres) — huit clés, plus deux pour le journal.
    cc_lien_title:"Lien de connexion de secours",
    cc_lien_hint:"Pour un pilote que la connexion Discord n'arrive pas à faire entrer. Le lien ouvre sa session une seule fois, pendant 24 heures. Ne le remettez qu'à lui : quiconque l'ouvre entre sous son nom. En émettre un nouveau annule le précédent.",
    cc_lien_btn:"Émettre un lien",
    cc_lien_copy:"Copier",
    cc_lien_copied:"Lien copié",
    cc_lien_until:"Valable une fois, jusqu'au {date} à {heure}.",
    cc_lien_refus:"Ce membre n'a pas le droit de connexion : un lien ne lui ouvrirait rien.",
    cc_lien_error:"Le lien n'a pas pu être émis.",
    cc_jr_title:"Journal des modifications",
    cc_jr_hint:"Chaque écriture du Centre : qui, quand, quoi, l'avant et l'après. Les plus récentes d'abord. Réservé aux administrateurs.",
    cc_jr_col_date:"Date",
    cc_jr_col_par:"Par",
    cc_jr_col_action:"Action",
    cc_jr_col_objet:"Objet",
    cc_jr_col_detail:"Détail",
    cc_jr_empty:"Rien n'est consigné depuis la mise en place du journal.",
    cc_jr_more:"Plus anciennes",
    cc_jr_error:"Impossible de lire le journal.",
    cc_jr_a_squadron_create:"Escadrille créée",
    cc_jr_a_squadron_edit:"Escadrille modifiée",
    cc_jr_a_squadron_crest:"Écusson posé",
    cc_jr_a_squadron_sleep:"Mise en sommeil",
    cc_jr_a_squadron_wake:"Réveil",
    cc_jr_a_squadron_leader:"Chef désigné",
    cc_jr_a_squadron_deputy:"Adjoint désigné",
    cc_jr_a_campaign_create:"Campagne créée",
    cc_jr_a_campaign_edit:"Campagne modifiée",
    cc_jr_a_campaign_delete:"Campagne supprimée",
    cc_jr_a_members_appel:"Appel au bouton",
    cc_jr_a_members_lien_secours:"Lien de secours émis",
    cc_jr_a_auth_lien_secours:"Lien de secours utilisé",
    cc_jr_a_rights_chef_role:"Rôle des chefs",
    cc_jr_a_rights_event_editors:"Éditeurs du planning",
    cc_jr_a_rights_app_access:"Accès à l'application",
    cc_jr_a_rights_debrief_access:"Accès à l'Escadre",
    cc_jr_a_rights_relances:"Destinataires des relances",
    cc_jr_a_rights_content:"Droits sur le contenu",
    cc_jr_a_wing_edit:"Escadre modifiée",
    cc_jr_a_wing_emblem:"Emblème posé",
    cc_jr_a_ref_type:"Type",
    cc_jr_a_ref_arme:"Arme",
    cc_jr_a_ref_import:"Référentiel importé",
    cc_jr_a_archives_sauvegarde:"Sauvegarde manuelle",
    cc_jr_a_archives_automatique:"Sauvegarde automatique réglée",
    // Lot « La réception du .rrlog de l'agent » (v1.0089) : le bloc « Serveur DCS » de l'écran Archives et ses deux gestes du journal.
    cc_agent_title:"Serveur DCS",
    cc_agent_hint:"L'agent du serveur DCS envoie ici le journal de chaque session jouée, que le Débrief lira. Il s'identifie par un jeton émis sur cet écran : un seul est actif à la fois.",
    cc_agent_actif:"Jeton actif, émis le {date} par {nom} · {envoi}",
    cc_agent_envoi_aucun:"aucun envoi reçu",
    cc_agent_envoi_le:"dernier envoi reçu le {date} à {heure}",
    cc_agent_aucun:"Aucun jeton : l'agent du serveur DCS ne peut rien envoyer.",
    cc_agent_emettre:"Émettre un jeton",
    cc_agent_remplacer:"Remplacer le jeton",
    cc_agent_revoquer:"Révoquer",
    cc_agent_conf_remplacer_titre:"Remplacer le jeton ?",
    cc_agent_conf_revoquer_titre:"Révoquer le jeton ?",
    cc_agent_conf_texte:"L'ancien jeton cesse de fonctionner tout de suite : le serveur DCS n'enverra plus rien tant que le nouveau n'est pas dans sa configuration.",
    cc_agent_conf_remplacer_ok:"Remplacer",
    cc_agent_conf_revoquer_ok:"Révoquer",
    cc_agent_jeton:"Jeton",
    cc_agent_adresse:"Adresse",
    cc_agent_copie:"Copié",
    cc_agent_une_fois:"Ce jeton ne sera plus jamais affiché. Remettez-le à l'administrateur du serveur DCS : il va dans readyroom_envoi.json, champ « jeton », et l'adresse dans le champ « adresse ».",
    cc_agent_recus:"Derniers fichiers reçus",
    cc_agent_col_recu:"Reçu le",
    cc_agent_col_mission:"Mission",
    cc_agent_col_theatre:"Théâtre",
    cc_agent_col_date:"Date de mission",
    cc_agent_col_taille:"Taille",
    cc_agent_col_etat:"État",
    cc_agent_etat_attente:"En attente de lecture",
    cc_agent_vide:"Aucun fichier reçu du serveur DCS.",
    cc_jr_a_agent_jeton_emis:"Jeton du serveur DCS émis",
    cc_jr_a_agent_jeton_revoque:"Jeton du serveur DCS révoqué",
    // Lot « L'accès invité » (v1.0070) : le bandeau, le mur, le bloc de l'écran Droits et le journal.
    invite_bandeau:"Accès invité · démonstration en lecture seule — jusqu'au {date}",
    invite_lecture_seule:"Accès invité : lecture seule.",
    cc_inv_title:"Invités — démonstration",
    cc_inv_hint:"Une personne hors du serveur Discord de l'escadre, autorisée par son identifiant Discord, pour lui montrer la Ready Room. Elle voit tout ce qu'un chef voit, <b>strictement en lecture seule</b>, et n'apparaît dans aucun tableau. Elle entre par « Se connecter avec Discord ».",
    cc_inv_hint_duree:"Trente jours, prolongeables. Une révocation prend effet à son geste suivant.",
    cc_inv_id_label:"Identifiant Discord",
    cc_inv_verifier:"Vérifier",
    cc_inv_compte:"Compte Discord : <b>{nom}</b> (@{username}) ·",
    cc_inv_inviter:"Inviter pour 30 jours",
    cc_inv_col_invite:"Invité",
    cc_inv_col_id:"Identifiant",
    cc_inv_col_par:"Invité par",
    cc_inv_col_jusqua:"Jusqu'au",
    cc_inv_col_entree:"Dernière entrée",
    cc_inv_prolonger:"Prolonger de 30 jours",
    cc_inv_revoquer:"Révoquer",
    cc_inv_vide:"Aucun invité.",
    cc_inv_jamais:"jamais",
    cc_jr_a_invites_ajout:"Invité ajouté",
    cc_jr_a_invites_prolongation:"Invitation prolongée",
    cc_jr_a_invites_revocation:"Invitation révoquée",
    cc_jr_a_invites_entree:"Entrée d'un invité",
    // Lot « Le rattachement des dépôts » (v1.0052) : les deux gestes du Débrief ; « Fichier » réemploie cc_jr_f_fichier.
    cc_jr_a_debrief_deplacer:"Fichier de mission déplacé",
    cc_jr_a_debrief_fusionner:"Missions fusionnées",
    cc_jr_f_mission:"Mission",
    cc_jr_f_absorbee:"Mission absorbée",
    cc_jr_f_designation:"Désignation",
    cc_jr_f_callsign:"Indicatif",
    cc_jr_f_full_name:"Nom complet",
    cc_jr_f_discord_role_id:"Rôle Discord",
    cc_jr_f_aircraft:"Appareils",
    cc_jr_f_liveries:"Livrées",
    cc_jr_f_default_liveries:"Livrées par défaut",
    cc_jr_f_nickname:"Surnom",
    cc_jr_f_name:"Nom",
    cc_jr_f_sim:"Simulateur",
    cc_jr_f_map_name:"Théâtre",
    cc_jr_f_status:"Statut",
    cc_jr_f_description:"Description",
    cc_jr_f_entres:"Entrés",
    cc_jr_f_sortis:"Sortis",
    cc_jr_f_role_id:"Rôle",
    cc_jr_f_profile_id:"Membre",
    cc_jr_f_role_ids:"Rôles",
    cc_jr_f_profile_ids:"Comptes",
    cc_jr_f_session_edit_role_ids:"Missions — modifier",
    cc_jr_f_event_edit_any_role_ids:"Planning — modifier tout",
    cc_jr_f_campaign_manage_role_ids:"Campagnes — gérer",
    cc_jr_f_campaign_delete_role_ids:"Campagnes — supprimer",
    cc_jr_f_period:"Période",
    cc_jr_f_sigle:"Sigle",
    cc_jr_f_tag:"Tag",
    cc_jr_f_libelle:"Libellé",
    cc_jr_f_categorie:"Catégorie",
    cc_jr_f_poses:"Posés",
    cc_jr_f_refuses:"Refusés",
    cc_jr_f_fichier:"Fichier",
    cc_jr_f_intervalle_h:"Fréquence (h)",
    cc_jr_f_garder:"Rétention",
    // Lot « La page Configuration du Centre » (v1.0106) : l'onglet, ses deux blocs et les trois actions du journal.
    nav_cc_configuration:"Config",
    cc_cfg_title:"Configuration",
    cc_cfg_hint:"Les réglages du serveur, gardés par la Ready Room. Réservé aux administrateurs ; chaque changement est inscrit au journal des Archives.",
    cc_cfg_error:"Impossible de charger la configuration.",
    cc_cfg_adm_title:"Administrateurs",
    cc_cfg_adm_hint:"Un administrateur ouvre tout le Centre, les sauvegardes, les invitations et les liens de secours. Les fondateurs sont fixés sur le serveur ; les autres se nomment ici.",
    cc_cfg_adm_col_nom:"Membre",
    cc_cfg_adm_col_statut:"Statut",
    cc_cfg_adm_col_depuis:"Nommé le",
    cc_cfg_adm_fondateur:"Fondateur",
    cc_cfg_adm_nomme:"Nommé",
    cc_cfg_adm_fondateur_note:"Se change sur le serveur",
    cc_cfg_adm_inconnu:"Compte {id}",
    cc_cfg_adm_choisir:"Choisir un membre",
    cc_cfg_adm_nommer:"Nommer",
    cc_cfg_adm_retirer:"Retirer",
    cc_cfg_adm_nommer_titre:"Nommer administrateur",
    cc_cfg_adm_nommer_texte:"{nom} pourra tout régler au Centre, cette page comprise, et nommer ou retirer d'autres administrateurs.",
    cc_cfg_adm_retirer_titre:"Retirer un administrateur",
    cc_cfg_adm_retirer_texte:"{nom} perd les droits d'administrateur ; les droits que lui donnent ses rôles restent.",
    cc_cfg_adm_retirer_soi:"Vous retirez vos propres droits d'administrateur : la page se rechargera sans la Configuration.",
    cc_cfg_reg_title:"Paramètres du serveur",
    cc_cfg_cle_absente:"La clé de chiffrement du serveur (CONFIG_KEY) manque ou est invalide : les secrets ne peuvent être ni lus ni enregistrés. Les autres réglages restent modifiables.",
    cc_cfg_col_reglage:"Réglage",
    cc_cfg_col_valeur:"Valeur",
    cc_cfg_col_action:"Action",
    cc_cfg_g_recit:"Le Récit du Rapport de mission",
    cc_cfg_g_digest:"Discord — le digest",
    cc_cfg_g_reponses:"Discord — les réponses",
    cc_cfg_g_tuiles:"Les tuiles de la carte",
    cc_cfg_g_suites:"Les suites (Mission Plan)",
    cc_cfg_g_fuseau:"Fuseau horaire",
    cc_cfg_l_REFERENCE_TZ:"Fuseau de l'escadre",
    cc_cfg_h_REFERENCE_TZ:"Le fuseau dans lequel la Ready Room range les jours, déroule les séries, écrit les heures des messages Discord et des rapports, et joue son passage de 6 h. Un nom de la base des fuseaux, comme Europe/Paris ou America/New_York. À régler à l'installation : un changement ne recalcule rien, et les séries suivent alors les heures d'été du nouveau fuseau.",
    cc_cfg_l_ANTHROPIC_API_KEY:"Clé de l'API Anthropic",
    cc_cfg_h_ANTHROPIC_API_KEY:"Sert à rédiger le Récit du Rapport de mission. Sans clé, ou sans crédit, le Récit ne se rédige pas.",
    cc_cfg_l_ANTHROPIC_MODEL:"Modèle de rédaction",
    cc_cfg_h_ANTHROPIC_MODEL:"L'identifiant du modèle qui rédige le Récit. Vide : le Récit ne se rédige pas.",
    cc_cfg_l_ANTHROPIC_EFFORT:"Effort de rédaction",
    cc_cfg_h_ANTHROPIC_EFFORT:"Plus l'effort est élevé, plus la rédaction réfléchit, et plus elle est lente et coûteuse. « Moyen » est le réglage éprouvé.",
    cc_cfg_effort_low:"Faible",
    cc_cfg_effort_medium:"Moyen",
    cc_cfg_effort_high:"Élevé",
    cc_cfg_effort_xhigh:"Très élevé",
    cc_cfg_effort_max:"Maximal",
    cc_cfg_modele_choisir:"Choisir un modèle",
    cc_cfg_modele_hors_liste:"(hors de la liste)",
    cc_cfg_modeles_source:"Les modèles actifs d'Anthropic, lus avec la clé de l'API.",
    cc_cfg_modeles_sans_cle:"Sans clé de l'API, la liste des modèles est indisponible : l'identifiant du modèle se saisit à la main.",
    cc_cfg_modeles_erreur:"Anthropic n'a pas répondu : la liste des modèles est indisponible, l'identifiant du modèle se saisit à la main.",
    cc_cfg_modeles_detail:"Raison : {detail}",
    cc_cfg_effort_incompatible:"Ce modèle n'accepte pas l'effort « {effort} » : choisir d'abord un autre effort.",
    cc_cfg_l_DISCORD_WEBHOOK_URL:"Adresse du webhook du digest",
    cc_cfg_h_DISCORD_WEBHOOK_URL:"Le salon Discord où part le planning de la semaine. L'adresse vaut accès : elle est gardée secrète. Vide : rien n'est posté.",
    cc_cfg_l_DISCORD_DIGEST_LOCALE:"Langue du digest",
    cc_cfg_h_DISCORD_DIGEST_LOCALE:"La langue des messages du digest dans Discord.",
    cc_cfg_l_DISCORD_DIGEST_TOKEN:"Jeton des mises à jour manuelles",
    cc_cfg_h_DISCORD_DIGEST_TOKEN:"Protège les mises à jour des messages Discord lancées à la main ou par un script. Vide : elles sont refusées ; la mise à jour de 6 h n'en a pas besoin.",
    cc_cfg_l_DISCORD_RSVP_ENABLED:"Réponses dans Discord",
    cc_cfg_h_DISCORD_RSVP_ENABLED:"Les membres répondent aux évènements depuis Discord, par les boutons du bot. Désactivé : le bot dort et seul le digest est posté.",
    cc_cfg_l_DISCORD_BOT_TOKEN:"Jeton du bot",
    cc_cfg_h_DISCORD_BOT_TOKEN:"Le jeton du bot Discord de la Ready Room (portail développeur de Discord). Ne le videz pas en désactivant les réponses : le bot en a besoin pour retirer ses messages.",
    cc_cfg_l_DISCORD_PUBLIC_KEY:"Clé publique de l'application",
    cc_cfg_h_DISCORD_PUBLIC_KEY:"64 caractères hexadécimaux, du portail développeur de Discord. Elle vérifie les boutons et la commande /readyroom.",
    cc_cfg_l_DISCORD_NOTIFY_CHANNEL_ID:"Salon des réponses",
    cc_cfg_h_DISCORD_NOTIFY_CHANNEL_ID:"L'identifiant du salon où le bot poste les évènements (17 à 20 chiffres).",
    cc_cfg_l_DISCORD_RSVP_HORIZON_DAYS:"Horizon des réponses (jours)",
    cc_cfg_h_DISCORD_RSVP_HORIZON_DAYS:"Seuls les évènements des prochains jours reçoivent un message, de 1 à 120 jours.",
    cc_cfg_l_TILES_UPSTREAM:"Serveur de tuiles",
    cc_cfg_h_TILES_UPSTREAM:"Le serveur interrogé quand une tuile de la carte n'est ni dans le miroir ni dans le cache. https:// seulement.",
    cc_cfg_l_WING_ID:"Clé de l'escadre",
    cc_cfg_h_WING_ID:"La clé sous laquelle Mission Plan et HQ rangent les réglages de l'escadre dans le navigateur des membres. Vide : tirée de la désignation, les espaces devenus des tirets. La changer fait perdre ces réglages. Lettres, chiffres, « . », « _ » et « - », 64 caractères au plus, le premier une lettre ou un chiffre.",
    cc_cfg_s_rempli:"Renseigné",
    cc_cfg_s_vide:"Vide",
    cc_cfg_s_remplace:"Remplacé",
    cc_cfg_s_illisible:"Illisible — à ressaisir",
    cc_cfg_s_modifie:"Modifié le {date} par {nom}",
    cc_cfg_s_repris:"Repris du serveur le {date}",
    cc_cfg_saisir:"Saisir",
    cc_cfg_remplacer:"Remplacer",
    cc_cfg_vider:"Vider",
    cc_cfg_enregistrer:"Enregistrer",
    cc_cfg_defaut:"Revenir au défaut",
    cc_cfg_defaut_val:"Par défaut : {v}",
    cc_cfg_defaut_aucun:"Par défaut : aucun",
    cc_cfg_oui:"Activé",
    cc_cfg_non:"Désactivé",
    cc_cfg_lang_fr:"Français",
    cc_cfg_lang_en:"Anglais",
    cc_cfg_vider_titre:"Vider ce secret",
    cc_cfg_vider_texte:"« {reglage} » sera effacé du serveur ; ce qui en dépend s'arrête jusqu'à une nouvelle saisie.",
    cc_cfg_err_valeur:"Valeur refusée : vérifiez son format.",
    cc_cfg_err_cle:"Clé de chiffrement absente : ce secret ne peut pas être enregistré.",
    cc_cfg_enregistre:"Enregistré.",
    cc_cfg_dos_title:"Dossiers du serveur",
    cc_cfg_dos_hint:"Branchés par Docker au démarrage, d'après le fichier .env du serveur. En lecture seule : ils se changent sur le serveur, et comptent au redémarrage suivant.",
    cc_cfg_dos_col_dossier:"Dossier",
    cc_cfg_dos_col_contenu:"Contenu",
    cc_cfg_dos_l_suites:"Les suites",
    cc_cfg_dos_h_suites:"Les fichiers de Mission Plan et de Mission Tools que la Ready Room sert à l'escadre.",
    cc_cfg_dos_l_tuiles:"Les tuiles de la carte DCS",
    cc_cfg_dos_h_tuiles:"Les archives de DCS Olympus extraites sur le serveur.",
    cc_cfg_dos_l_tuiles_gardees:"Les tuiles gardées",
    cc_cfg_dos_h_tuiles_gardees:"Les tuiles venues d'Olympus et gardées par la Ready Room ; ce dossier se remplit seul.",
    cc_cfg_dos_un:"1 fichier",
    cc_cfg_dos_n:"{n} fichiers",
    cc_cfg_dos_plafond:"{n} fichiers ou plus",
    cc_cfg_dos_vide:"Vide",
    cc_cfg_dos_vide_aide:"Aucun fichier : la ligne {variable} du .env manque, ou pointe vers un dossier vide.",
    cc_cfg_dos_vide_aide_tuiles_gardees:"Aucune tuile gardée pour l'instant : le dossier se remplit à l'usage de la carte.",
    cc_cfg_dos_absent:"Introuvable",
    cc_cfg_dos_absent_aide:"Le dossier {chemin} n'existe pas dans le conteneur : voir docker-compose.yml.",
    cc_cfg_dos_erreur:"Impossible de lire les dossiers du serveur.",
    cc_jr_a_reglage_edit:"Réglage modifié",
    cc_jr_a_admin_nommer:"Administrateur nommé",
    cc_jr_a_admin_retirer:"Administrateur retiré",
    cc_jr_f_valeur:"Valeur",
    cc_camp_act_edit:"Modifier",
    cc_camp_act_delete:"Supprimer",
    cc_camp_create_title:"Créer une campagne",
    cc_camp_create_hint:"Seul le nom est obligatoire. Deux campagnes ne peuvent pas porter le même nom sur un même simulateur — la casse n'y change rien.",
    cc_camp_edit_title:"Modifier « {name} »",
    cc_camp_edit_hint:"Le nom reste unique par simulateur. Passer le statut à « Close » n'efface rien : la campagne et ses missions restent consultables.",
    cc_camp_field_desc_ph:"Description — apparaîtra sur l'écran Campagnes du module Escadre",
    cc_camp_submit_create:"Créer",
    cc_camp_submit_save:"Enregistrer",
    cc_camp_create_deny_name:"Le nom de la campagne est obligatoire.",
    cc_camp_sim_locked:"Le simulateur ne peut plus être changé : {count} missions sont rattachées à cette campagne. Les déplacer sur un autre simulateur les rendrait invisibles dans les sélecteurs. Le champ est verrouillé, pas masqué.",
    cc_camp_delete_confirm:"Supprimer {name} ? Aucune mission n'y est rattachée. L'effet est immédiat et définitif.",
    cc_camp_delete_deny:"Impossible de supprimer {name} : {count} missions y sont rattachées. Une campagne qui a servi ne s'efface pas — elle se clôt, et reste consultable. Pour la supprimer malgré tout, détache d'abord ses missions depuis l'édition de session.",
    cc_camp_note_close:"Fermer",
    // Lot « Le nom qu'on retient » v0.9917 -- bordereau d'identification
    // (§6 du brief), mécanisme UNIQUE remplaçant l'ancien "Identifier ce
    // vol"/"Annuler l'identification" (v0.9913/v0.9915, clés idov_*/
    // unidentify_* retirées : le champ de saisie libre a disparu, il ne
    // reste que la désignation d'un membre). 25 clés neuves.
    slip_hd_title:"Annotation du bureau",
    slip_hd_who:"Réservé au commandement",
    slip_select_label:"Ce vol est un membre de l'escadre",
    slip_select_placeholder:"— choisir —",
    slip_select_no_squadron:"Sans escadrille",
    slip_memo:"Le nom {segment} sera retenu pour {who}. Ses prochains vols sous ce nom seront rattachés sans que vous reveniez ici.",
    slip_cancel:"Annuler",
    slip_attach:"Rattacher",
    slip_attach_error:"Choisissez un membre avant de rattacher.",
    slip_attach_done:"Vol rattaché ✓",
    slip_attach_fail:"Échec du rattachement.",
    slip_done_alias:"Rattaché à {who} par un nom retenu, d'après l'indicatif {callsign}.",
    slip_done_engine:"Rattaché à {who} par le moteur, d'après l'indicatif {callsign}.",
    slip_done_manual:"Rattaché à {who} à la main.",
    slip_correct:"Corriger",
    slip_detach:"Détacher",
    slip_detach_running:"Détachement en cours…",
    slip_detach_done:"Vol détaché ✓",
    slip_detach_fail:"Échec du détachement.",
    slip_forget:"Oublier ce nom",
    slip_forget_running:"Oubli en cours…",
    slip_forget_done:"Nom oublié ✓",
    slip_forget_fail:"Échec de l'oubli.",
  },
  en:{
    signin:"Sign in with Discord",
    back:"Back",
    connected:"Connected",
    station_planif:"Scheduling",
    station_debrief:"Wing",
    station_command:"Command Center",
    cc_station_sans_role:"Leader role missing",
    cc_station_sans_role_toast:"{squadron} leader without the Discord leader role: ask an administrator for it.",
    status_operational:"Operational",
    open:"Open",
    debrief_construction_toast:"Wing module — access is granted by an administrator.",
    adresse_introuvable:"This page no longer exists or is not open to you.",
    landing_title:"{wing} — Ready Room",
    landing_sub:"Squadron internal portal — flight scheduling, attendance and debriefing.",
    nav_planche:"The Board",
    nav_hebdo:"Weekly Table",
    theme_dark:"Dark",
    theme_light:"Greaseboard",
    theme_system:"System",
    help_btn:"Manual — this screen",
    lang_name:"EN",
    month_prev:"Previous month",
    month_next:"Next month",
    week_prev:"Previous week",
    week_next:"Next week",
    view_month:"Month",
    view_week:"Week",
    add_event:"+ Event",
    filter_all:"All",
    type_entrainement:"Training",
    type_mission:"Mission",
    type_campagne:"Campaign",
    type_jeulibre:"Free play",
    today:"Today",
    today_abbr:"Today",
    to_answer:"To answer",
    my_answer:"My answer",
    my_choices:"My choices — optional",
    agenda_upcoming:"Upcoming",
    filters_show:"Show",
    upcoming_until:"until {date}",
    upcoming_none:"Nothing planned.",
    upcoming_none_todo:"Nothing awaits your answer.",
    agenda_all:"Whole month",
    agenda_empty_upcoming:"No upcoming events this month. Switch to \"Whole month\" to see the past.",
    section_planche:"The Board",
    section_hebdo:"Weekly Attendance Table",
    hebdo_current:"Current week",
    hebdo_next:"Next week",
    hebdo_empty:"No events this week.",
    hebdo_no_rsvp:"No sign-ups this week.",
    hebdo_totals:"Summary",
    hebdo_aircraft:"Aircraft",
    hebdo_missions:"Missions",
    hebdo_card_empty:"No one signed up",
    rsvp_title:"RSVP",
    rsvp_present:"Present",
    rsvp_maybe:"Maybe",
    rsvp_absent:"Absent",
    rsvp_series_label:"↻ Apply “{state}” to the whole series",
    rsvp_series_apply:"Apply",
    rsvp_series_done:"Applied to {n} dates ✓",
    rsvp_series_none:"No upcoming dates in the series",
    creator:"Created by",
    edit:"Edit",
    delete:"Delete",
    close:"Close",
    save:"Save",
    cancel:"Cancel",
    recurring:"Recurring",
    recurrence_scope:"This occurrence / whole series",
    recurrence_this:"This occurrence",
    recurrence_all:"Whole series",
    roster:"Roster",
    paris_ref:"Europe/Paris ref.",
    new_event_title:"New event",
    field_title:"Title",
    field_type:"Type",
    field_date:"Date",
    field_time:"Time",
    field_game:"Game (if Free play)",
    field_platform:"Platform",
    field_map:"Map",
    field_desc:"Description",
    field_duration:"Duration (min)",
    field_recurring:"Recurring (weekly)",
    field_weekdays:"Days",
    field_interval:"Interval (weeks)",
    field_end:"End",
    end_none:"No end",
    end_until:"Until",
    end_count:"Number of occurrences",
    edit_event_title:"Edit event",
    confirm_delete:"Delete this event?",
    confirm_delete_seul:"The event is removed from the Board{rep}.",
    confirm_delete_occ:"Only the <b>{jour}</b> occurrence is removed{rep}. The series goes on.",
    confirm_delete_serie:"<b>Every occurrence of the series</b> is removed from the Board, with their responses.",
    confirm_rep_un:", with <b>its response</b>",
    confirm_rep_n:", with its <b>{n} responses</b>",
    serie_eff_titre:"Before saving",
    serie_eff_texte:"This change erases {liste}.",
    serie_eff_rep_un:"<b>1 upcoming answer</b>",
    serie_eff_rep_n:"<b>{n} upcoming answers</b>",
    serie_eff_date_un:"<b>1 changed or cancelled date</b>",
    serie_eff_date_n:"<b>{n} changed or cancelled dates</b>",
    serie_eff_et:" and ",
    serie_eff_ok:"Erase and save",
    evt_modifie:"This event was changed in the meantime: reopen it to see the current version.",
    nav_plus:"More",
    error_generic:"Something went wrong.",
    error_stream_lost:"Connection lost — reload the page to sign in again.",
    loading:"Loading…",
    toast_created:"Event created ✓",
    toast_updated:"Event updated ✓",
    toast_deleted:"Event deleted ✓",
    week_of:"Week of",
    to:"to",
    no_events:"No events this month.",
    logout:"Sign out",
    external_tools_title:"Other tools",
    opens_new_tab:"(opens in a new tab)",
    manual_tile:"Pilot’s Manual",   // Lot « Le Manuel Pilote, le socle » : la tuile de l'accueil
    pref_aircraft_label:"Desired aircraft",
    pref_missions_label:"Mission types",
    pref_add:"+ Add",
    pref_filter_ph:"Filter…",
    pref_no_match:"No matching aircraft.",
    game_other:"other",
    day_no_events:"No event this day",
    day_create:"+ Create this day",
    new_tag:"NEW",
    form_group_quoi:"What",
    form_group_quand:"When",
    form_group_recurrence:"Recurrence",
    nav_missions:"Missions",
    nav_accueil:"Home",
    nav_pilotes:"Record",
    nav_campagnes:"Campaigns",
    nav_escadrilles:"Squadrons",
    // Lot 3.2b — Command Center, Squadrons screen
    nav_cc_escadre:"Wing",
    nav_cc_escadrilles:"Squadrons",
    nav_cc_membres:"Members",
    nav_cc_droits:"Rights",
    nav_cc_campagnes:"Campaigns",
    nav_cc_referentiels:"Ref",
    nav_cc_archives:"Arch",
    cc_squadrons_title:"Squadrons",
    cc_sqn_col_designation:"Identifier",
    cc_sqn_col_callsign:"Callsign",
    cc_sqn_col_fullname:"Full name",
    cc_sqn_aircraft:"Aircraft",
    cc_sqn_aircraft_add:"＋ Aircraft…",
    cc_sqn_aircraft_other:"Other…",
    cc_sqn_aircraft_other_ph:"Other aircraft",
    cc_sqn_aircraft_other_ok:"Add",
    cc_sqn_liv_titre:"Liveries",
    cc_sqn_liv_defaut_titre:"Default livery",
    cc_sqn_liv_tag_custom:"Custom",
    cc_sqn_liv_tag_jeu:"Game",
    cc_sqn_liv_nom_ph:"Livery folder name",
    cc_sqn_liv_nom_aria:"Livery name",
    cc_sqn_liv_jeu_choisir:"Choose a game livery…",
    cc_sqn_liv_jeu_aria:"Game livery",
    cc_sqn_liv_jeu_appareil_aria:"Aircraft",
    cc_sqn_liv_retirer:"Remove",
    cc_sqn_liv_retirer_aria:"Remove livery",
    cc_sqn_liv_ajout_jeu:"+ Game livery",
    cc_sqn_liv_ajout_custom:"+ Custom livery",
    cc_sqn_liv_aide:"A custom livery is written as its folder name in DCS.",
    cc_sqn_liv_aucune:"No livery.",
    cc_sqn_liv_defaut_aucune:"None",
    cc_sqn_liv_defaut_esc:"Squadron liveries",
    cc_sqn_liv_defaut_jeu:"Other game liveries",
    cc_sqn_liv_defaut_aria:"Default livery {aircraft}",
    cc_sqn_liv_types:"{n} DCS types",
    cc_sqn_liv_sans:"{aircraft}: no livery.",
    cc_sqn_liv_sans_appareil:"Declare an aircraft first.",
    cc_sqn_liv_err_ligne:"Give this livery a name and at least one aircraft.",
    cc_sqn_liv_err_double:"This livery is already in the list.",
    cc_sqn_liv_res_1:"1 livery",
    cc_sqn_liv_res_n:"{n} liveries",
    cc_sqn_liv_res_def_1:"1 default",
    cc_sqn_liv_res_def_n:"{n} defaults",
    cc_sqn_liv_ecartee:"Default livery {aircraft} set aside: {squadron} takes precedence",
    cc_sqn_nickname:"Nickname",
    cc_sqn_col_status:"Status",
    cc_sqn_col_role:"Discord role",
    cc_sqn_col_actions:"Actions",
    cc_sqn_status_actif:"Active",
    cc_sqn_status_sommeil:"Dormant",
    cc_sqn_empty:"No squadron registered.",
    cc_sqn_error:"Couldn't load squadrons.",
    cc_sqn_retry:"Retry",
    cc_sqn_partial:"At least one active squadron has no linked Discord role — its members won't resolve automatically.",
    deposer:"Upload",
    deposer_soon:"Upload available in the next batch",
    module_soon:"Coming soon",
    retry:"Retry",
    // Lot D2③ — Missions screen
    // Lot 1.5b §10 — masthead (sheet chassis), Missions/Session/Flight.
    // Session created now even though its screen ships in 1.4d.
    cart_title_missions:"MISSIONS",
    cart_sub_missions:"{wing} · Flown missions register",
    cart_title_session:"SESSION",
    cart_sub_session:"{wing} · Mission report",
    cart_title_flight:"FLIGHT",
    cart_sub_flight:"{wing} · Flight record",
    missions_empty:"No missions uploaded yet",
    missions_no_match:"No missions match these filters.",
    missions_no_date:"No date",
    missions_word:"mission",
    chip_all_squadrons:"All squadrons",
    chip_all_years:"All",
    chip_all_months:"All months",
    meta_pilots:"identified pilots",
    meta_anon:"anonymous",
    meta_flights:"flights",
    soiree_titre:"The evening's debrief",
    soiree_aucune:"No session filed that day.",
    soiree_planifiee:"Planned evening",
    meta_kills:"kills",
    acmi_on:"ACMI",
    acmi_off:"No ACMI",
    doc_label:"documented",
    session_error_retry:"Retry",
    session_report_cta:"▸ Report",
    session_doc_title:"Mission documentation",
    session_doc_cap:"of pilots have filed their debrief",
    session_doc_sources:"Sources",
    session_cov_kind_acmi:"ACMI TacView",
    session_cov_kind_debrief:"debrief",
    session_roster_title:"Roster",
    session_roster_flights_word:"flights",
    session_th_pilot:"Pilot",
    session_th_aircraft:"Aircraft",
    session_th_time:"Duration",
    session_th_kills:"Kills",
    session_th_shots:"Shots",
    session_th_issue:"Outcome",
    session_th_data:"Data",
    session_issue_rtb:"RTB",
    session_issue_kia:"KIA",
    session_issue_eject:"Ejected",
    session_issue_none:"—",
    session_badge_reliable:"Debrief uploaded",
    session_badge_partial:"Reconstructed",
    session_badge_anon:"Anonymous flight",
    session_member_mark_title:"Ready Room member",
    session_member_mark_short:"member",
    session_graveyard_title:"Destruction summary",
    session_facts_title:"Highlights",
    cart_title_escadre:"WING",
    cart_sub_escadre:"{wing} · Order of battle",
    escadre_kick:"Order of battle",
    escadre_actives_n:"{n} active squadrons",
    escadre_pilotes_n:"{n} pilots",
    escadre_pilotes_un:"1 pilot",
    escadre_etat_title:"Wing record",
    escadre_designation:"Designation",
    escadre_nom_complet:"Full name",
    escadre_periode:"Period",
    escadre_sim:"Simulator",
    escadre_actives:"Active squadrons",
    escadre_sommeil:"Dormant squadrons",
    escadre_effectif:"Documented strength",
    escadre_orbat_title:"Order of battle",
    escadre_orbat_actives:"Active",
    escadre_orbat_sommeil:"Dormant",
    escadre_act_pilotes:"Active pilots",
    escadre_act_heures:"Flight hours",
    escadre_act_missions:"Missions",
    escadre_act_campagnes:"Campaigns",
    escadre_org_title:"Wing organisation chart",
    escadre_role_leader:"Leader",
    escadre_role_deputy:"Deputy",
    escadre_free:"Free agents",
    escadre_free_sub:"no squadron",
    cart_title_accueil:"COMMAND POST",
    cart_sub_accueil:"{wing} · Wing dashboard",
    acc_chiffres_title:"The wing in figures",
    acc_campagnes_title:"Ongoing campaigns",
    acc_aucune_campagne:"No ongoing campaign.",
    acc_missions_title:"Latest missions",
    acc_escadrilles_title:"Squadrons",
    acc_destructions_title:"Wing kills — last {n} days",
    acc_msn:"{n} msn",
    acc_vols:"{n} flights",
    cart_title_escadrille:"SQUADRON",
    cart_sub_escadrille:"{wing} · Unit file",
    cart_title_membre:"SUMMARY SHEET",
    cart_sub_membre:"{wing} · Open to the wing",
    esq_kick:"Unit file",
    esq_actif:"Active",
    esq_etat_title:"Unit record",
    esq_identifiant:"Identifier",
    esq_nom_complet:"Full name",
    esq_callsign:"Callsign",
    esq_escadre:"Wing",
    esq_dotation:"Aircraft",
    esq_effectif:"Active strength",
    esq_org_title:"Organisation chart",
    esq_act_title:"Unit activity",
    esq_act_missions:"Missions",
    esq_act_heures:"Hours",
    esq_act_sorties:"Sorties",
    esq_act_pilotes:"Pilots who flew",
    mbr_kick:"Member · {sq}",
    mbr_ancien:"former member",
    mbr_actif:"Active",
    mbr_archive:"Archived on {d}",
    mbr_part_title:"Participation",
    mbr_missions:"Missions",
    mbr_temps:"Flight time",
    mbr_appareils:"Aircraft",
    mbr_depuis:"Since",
    mbr_servis_title:"Aircraft flown",
    mbr_msn:"{n} msn · {h} h",
    mbr_barrettes_title:"Campaign ribbons",
    mbr_aucune_barrette:"No campaign flown.",
    mbr_missions_title:"Latest missions",
    mbr_aucune_mission:"No identified flight.",
    mbr_error:"The sheet could not be loaded.",
    // Lot « L'écran A » : the connected pilot's personal file (R208, R209, R212).
    cart_title_pilotes:"Personnel file",
    cart_sub_pilotes:"{wing} · Holder only",
    pil_stamp:"PERSONAL",
    pil_bilan_title:"Career record",
    pil_destr_title:"Kills by category",
    pil_menaces_title:"Threats faced",
    pil_carnet_title:"Logbook",
    // Batch « Mission or training » — the Dossier switch
    pil_filtre_label:"Kills and accuracy",
    pil_filtre_tout:"All",
    pil_filtre_missions:"Missions",
    pil_filtre_training:"Training",
    pil_valid:"Confirmed kills",
    pil_air:"Air victories",
    pil_sol:"Ground targets",
    pil_perdus:"Aircraft lost",
    pil_ejections:"Ejections",
    pil_ratio_cap:"kills per aircraft lost",
    pil_sans_perte:"No loss",
    pil_sans_perte_cap:"no aircraft lost",
    pil_doc_cap:"Flights documented by your uploads: {f} of {n}.",
    pil_doc_partiel:"Precision covers those flights only.",
    pil_largages:"{n} releases",
    // Lot « L'efficacité par arme au Dossier » : sous une arme, combien des cibles touchées le pilote a détruites.
    pil_eff_1_1:"{d} destroyed of {n} hit",
    pil_eff_1_n:"{d} destroyed of {n} hit",
    pil_eff_n_n:"{d} destroyed of {n} hit",
    pil_tout:"Show all ({n})",
    pil_voir_f:"What the wing sees of you →",
    cd_mes_cartes:"My DCS maps",
    cd_cartes:"DCS maps",
    cd_escadre_titre:"Wing DCS maps",
    cd_payantes:"Paid",
    cd_gratuites:"Free",
    cd_gratuite:"free",
    cd_enregistrer:"Save",
    cd_modifier:"Edit",
    cd_replier:"Collapse",
    cd_non_declarees:"Not declared yet.",
    cd_aucune:"No DCS map.",
    cd_declarees:"Declared on {date} · {n} map{s}.",
    cd_pilote:"Pilot",
    cd_non_declare:"not declared",
    cd_escadre:"Wing",
    cd_possedee:"owned",
    pil_vide:"Your file will fill up with your first recorded flight.",
    pil_prec_vide:"Precision is read on flights documented by your own upload.",
    pil_prec_aucun:"No shot recorded on your documented flights.",
    pil_menaces_vide:"No threat recorded on your flights.",
    pil_inconnu:"Unknown",
    pil_engag_un:"1 engagement",
    pil_engag_n:"{n} engagements",
    pil_vic_un:"1 victory",
    pil_vic_n:"{n} victories",
    pil_perte_un:"1 loss",
    pil_perte_n:"{n} losses",
    pil_dernier:"last flight {d}",
    // Lot « L'écran C — la fiche campagne » : the register and the file.
    cart_title_campagnes:"CAMPAIGNS",
    cart_sub_campagnes:"{wing} · Campaign register",
    cart_title_campagne:"CAMPAIGN",
    cart_sub_campagne:"{wing} · Campaign file",
    cmp_registre_title:"Campaign register",
    cmp_en_cours:"Ongoing",
    cmp_closes:"Closed",
    cmp_close:"Closed",
    cmp_aucune:"No campaign recorded.",
    cmp_kick:"Campaign file",
    cmp_ordre_title:"Operations order",
    cmp_theatre:"Theatre",
    cmp_periode:"Period",
    cmp_periode_en_cours:"{d} → ongoing",
    cmp_sim:"Simulator",
    cmp_sorties:"Sorties",
    cmp_pilotes:"Pilots",
    cmp_missions_title:"Campaign missions",
    cmp_aucune_mission:"No mission attached.",
    cmp_participants_title:"Participants",
    cmp_aucun_participant:"No identified pilot.",
    cmp_bilan_title:"Campaign record — wing facts",
    cmp_introuvable:"Campaign not found.",
    cmp_erreur:"Campaigns could not be loaded.",
    escadre_error:"The wing could not be loaded.",
    session_mixed_title:"Weapon names to check",
    session_mixed_note:"One burst carries several weapon names: two logs may name the same weapon differently, or the burst really mixes two munitions, such as a bomb and its submunitions. Visible to editors only.",
    // Lot 1.4d §6.8/§6.9 — the 3 new keys for the DA port of the Session
    // screen, one per note extracted from body_missions.html. No other
    // key is created by this lot.
    // Révision ④.1 — admin session delete (chgt 4)
    debrief_delete_session_title:"Delete session",
    debrief_toast_session_deleted:"Session deleted ✓",
    debrief_delete_forbidden:"Admin only",
    debrief_suppr_titre:"Delete this session?",
    debrief_suppr_texte:"“{titre}” is removed from the register, with {nv} flight{sv}, {nd} uploaded file{sd}, the events and the narrative.",
    slip_detach_titre:"Detach this flight?",
    slip_detach_texte:"The flight stays without a pilot and the engine won't reclaim it.",
    slip_forget_titre:"Forget this name?",
    slip_forget_texte:"Future flights under this callsign will no longer be attached automatically.",
    recompute_titre:"Recompute this session?",
    recompute_texte:"Everything is recomputed from the uploaded files. Manual identity overrides are preserved.",
    recompute_go:"Recompute",
    recompute_all_titre:"Recompute stale sessions?",
    recompute_all_texte:"{n} session{s} to recompute from their files. This can take several minutes.",
    recompute_all_go:"Recompute all",
    debrief_delete_redaction:"A narrative is being drafted for this mission: try again once it is finished.",
    // Lot D2③ — Upload modal
    deposer_modal_type:"Feed the debrief",
    deposer_modal_title:"Upload files",
    deposer_dz_big:"Drop an ACMI or a debrief.log",
    deposer_dz_sub:".acmi (TacView) · debrief.log — or click to browse",
    deposer_dz_big_touch:"Tap to choose your files",
    deposer_dz_sub_touch:".acmi (TacView) · debrief.log",
    deposer_depositor_label:"Who is uploading this debrief?",
    deposer_depositor_note:"A debrief has no reliable identity: you must declare the pilot. The mission is attached automatically (nothing else to pick).",
    deposer_me:"me",
    kind_debrief:"debrief.log (DCS client)",
    kind_acmi:"ACMI TacView",
    deposer_remove_file:"Remove",
    deposer_in_progress:"Uploading…",
    deposer_submit:"Upload",
    deposer_again:"Upload more files",
    deposer_noop:"Already uploaded — no change",
    deposer_attached_to:"Attached to",
    deposer_n_uploads:"Uploads (files)",
    deposer_n_flights:"Flights",
    deposer_n_kills:"Kills",
    // Batch D2⑤ — Flight screen (single-life detail)
    flight_stat_kills:"Kills",
    flight_stat_time:"Duration",
    // Lot « Les heures de jour et de nuit » (v1.0068).
    jn_de_jour:"day",
    jn_de_nuit:"night",
    flight_periode_jour:"Day flight",
    flight_periode_nuit:"Night flight",
    flight_periode_corrigee:"corrected",
    flight_periode_corriger:"Correct to: {p}",
    flight_periode_fail:"The correction failed.",
    flight_stat_altmax:"Max alt.",
    flight_stat_bilan:"Score (K−D)",
    flight_summary_title:"Flight summary",
    flight_timeline_title:"Flight log",
    flight_timeline_empty:"No timestamped events for this flight.",
    flight_tag_phase:"phase",
    flight_tag_kill:"kill",
    flight_tag_threat:"threat",
    flight_tag_shot:"shot",
    flight_tag_collab:"collaboration",
    flight_tag_destruction:"destruction",
    // Lot « Le journal dit quand un tir touche » : a hit target that survives,
    // and a destruction by a wreck's explosion.
    flight_tag_touche:"hit",
    flight_tag_collateral:"collateral",
    flight_phase_takeoff:"Takeoff",
    // Reserved (R137): the engine folds hops, the front has not shown them
    // since v0.9992. Kept for the day it shows them again.
    flight_phase_saut:"Hop",
    flight_phase_land:"Landing",
    flight_phase_crash:"Crash",
    flight_phase_eject:"Ejection",
    flight_phase_pilot_dead:"Pilot down",
    flight_phase_engine_startup:"Engine start",
    flight_phase_engine_shutdown:"Engine shutdown",
    flight_precision_title:"Weapon precision",
    flight_precision_empty:"No shots recorded for this flight.",
    flight_releases_word:"releases",
    flight_releases_tag:"releases",
    // Lot « L'écran de la précision » : les types d'armes, et ce que comptent les nombres.
    prec_cat_missiles:"Missiles",
    prec_cat_roquettes:"Rockets",
    prec_cat_bombes:"Bombs",
    prec_cat_sousmun:"Cluster munitions",
    prec_cat_canon:"Gun",
    prec_cat_autres:"Other",
    prec_larg_1:"{n} dispenser released",
    prec_larg_n:"{n} dispensers released",
    prec_salve_1:"in {n} salvo",
    prec_salve_n:"in {n} salvos",
    prec_roq_1:"{n} rocket fired",
    prec_roq_n:"{n} rockets fired",
    prec_obus_1:"{n} round",
    prec_obus_n:"{n} rounds",
    prec_raf_1:"in {n} burst",
    prec_raf_n:"in {n} bursts",
    prec_rafbut_1:"{n} burst on target",
    prec_rafbut_n:"{n} bursts on target",
    flight_threats_title:"Threats faced",
    flight_threats_none_note:"No incoming hits. Unguided fire without a declared target stays invisible (a DCS data limitation).",
    flight_kills_title:"Destruction summary",
    flight_kills_frat_un:"friendly-fire kill, excluded",
    flight_kills_frat:"friendly-fire kills, excluded",
    flight_threats_empty:"No threats recorded for this flight.",
    flight_grav_aimed:"Aimed",
    flight_grav_hit:"Hit",
    flight_grav_down:"Downed",
    // Lot 1.5 — "Incomplete" stamp (brief §2.3)
    flight_stamp_incomplete:"Incomplete",
    // Batch D2⑤ — Mission report modal
    report_modal_title:"Mission report",
    // Batch 1.6 §5.1 (R-A) — constant form label
    report_form_number:"FORM 4V-12 · REPORT",
    report_toggle_narrative:"Narrative",
    report_toggle_raw:"Timestamped raw",
    report_note:"Narrative written by a language model from facts assembled by the server (no figure is ever invented).",
    report_empty:"Not enough data yet to generate a report.",
    // Batch R2 §5 — Narrative drafting by a language model, frozen in the database
    report_generate_btn:"Draft",
    report_regenerate_btn:"Rewrite",
    report_generating:"Drafting…",
    report_stamp_a_corriger:"Needs update",
    report_loading:"Loading report…",
    report_not_generated:"No narrative drafted yet.",
    // Batch French source-of-truth §2⑤ — shown in EN when only the
    // translation is missing (the French text already exists)
    report_translation_pending:"Translation in progress…",
    report_translation_unavailable:"Translation unavailable.",
    report_gen_error_generic:"Drafting failed. Try again later.",
    // Batch "Debrief engine polish" — cap refusal (429) of drafting
    report_cap_reached:"Generation cap reached for this session (temporary: it frees up as the hour goes by, try again later).",
    // Batch R6 §6 — "in progress" state, carried by reads, never by the channel
    report_busy_by:"Drafting by {name}…",
    report_busy_conflict:"A draft is already running for this session.",
    report_stale_blocked:"This session's stats need recomputing: drafting waits for the recompute.",
    // Batch 2.1 — mission naming and wing note
    deposer_mission_name_label:"Mission name",
    deposer_wing_note_label:"Note for the wing",
    deposer_mission_name_hint:"The name only applies if the mission doesn't already have one.",
    deposer_mission_created:"New mission created",
    deposer_mission_joined:"Attached to an existing mission",
    deposer_name_applied:"Name saved",
    deposer_name_already_set:"Name already set",
    deposer_note_applied:"Note saved",
    deposer_note_already_set:"Note already set",
    // Batch 2.3 — the campaign as an entity
    deposer_campaign_label:"Campaign",
    campaign_none_option:"None",
    deposer_campaign_conflict:"The session is already attached to another campaign: the choice was not applied.",
    session_edit_campaign_label:"Campaign",
    // Batch « Mission or training » — the type of a session
    nature_label:"Type",
    nature_mission:"Mission",
    nature_training:"Training",
    nature_stamp:"Training",
    nature_stamp_sub:"EXERCISE · EXERCISE",
    deposer_nature_label:"Session type",
    error_field_too_long:"This field exceeds the allowed length.",
    session_edit_cta:"Edit",
    session_edit_name_label:"Mission name",
    session_edit_note_label:"Note for the wing",
    session_edit_save:"Save",
    session_edit_cancel:"Cancel",
    session_edit_saved:"Changes saved ✓",
    recompute_cta:"Recalc.",
    recompute_running:"Recomputing…",
    recompute_done:"Session recomputed ✓",
    recompute_error:"Recompute failed.",
    // Lot Fraîcheur v0.9939 (brief §9) : four new keys.
    stale_mark:"needs recompute",
    recompute_all_cta:"Recompute {n} session{s}",
    recompute_all_toast:"{n} session(s) recomputed ✓",
    // Lot « Le rattachement des dépôts » (v1.0052): the mark, the provenance, moving, merging.
    verif_mark:"To check",
    verif_mark_title:"A file is attached here by the header of a DCS sample mission",
    src_move_cta:"Move…",
    src_prov_titre:"attached by its title",
    src_prov_contenu:"attached by its content — the header named “{t}”",
    src_prov_manuel:"moved by hand by {nom}",
    src_prov_exemple:"attached by its title — header of a DCS sample mission",
    src_move_title_debrief:"Move {dep}'s debrief to…",
    src_move_title_acmi:"Move {dep}'s ACMI to…",
    src_move_files:"{n} file{s}",
    src_move_new:"A new mission",
    src_move_none:"No other mission within three days.",
    src_move_note:"Both missions are recomputed. A mission left without files disappears.",
    src_move_go:"Move",
    src_move_done:"File moved ✓",
    merge_label:"Merge with another mission",
    merge_none:"— none —",
    merge_cta:"Merge…",
    merge_confirm:"“{t}” will be merged into this mission: its {n} file{s} join it, then it disappears with its name, note and report. This mission keeps its own.",
    merge_confirm_un:"“{t}” will be merged into this mission: its file joins it, then it disappears with its name, note and report. This mission keeps its own.",
    merge_go:"Merge",
    merge_done:"Missions merged ✓",
    session_wing_note_label:"Wing note:",
    cc_members_title:"Members",
    cc_mbr_col_member:"Member",
    cc_mbr_col_rank:"Rank",
    cc_mbr_col_admin:"Admin",
    cc_mbr_col_seen:"Last login",
    cc_mbr_rank_leader:"Squadron leader",
    cc_mbr_rank_deputy:"Deputy",
    cc_mbr_rank_member:"Member",
    cc_mbr_admin_yes:"Admin",
    cc_mbr_empty:"No members registered.",
    cc_mbr_error:"Unable to load members.",
    cc_mbr_retry:"Retry",
    cc_appel_last:"Last roll call",
    cc_appel_btn:"Call the roll",
    cc_appel_running:"Roll call running…",
    cc_appel_none:"No change.",
    cc_appel_and:"and",
    cc_appel_out_one:"{names} leaves the roster",
    cc_appel_out_n:"{names} leave the roster",
    cc_appel_move_one:"{names} moves to {sq}",
    cc_appel_move_n:"{names} move to {sq}",
    cc_appel_fa_one:"{names} becomes a Free Agent",
    cc_appel_fa_n:"{names} become Free Agents",
    cc_appel_back_one:"{names} is back on the roster",
    cc_appel_back_n:"{names} are back on the roster",
    cc_appel_in_one:"{names} joins {sq}",
    cc_appel_in_n:"{names} join {sq}",
    cc_appel_in_fa_one:"{names} joins as a Free Agent",
    cc_appel_in_fa_n:"{names} join as Free Agents",
    cc_appel_list_ko:"server not listed ({reason}): nobody could join",
    cc_appel_error:"Roll call stopped — {reason}. Nothing was written.",
    cc_mbr_search_ph:"Search a member",
    cc_mbr_count:"{n} member{s}",
    cc_relances_n:"{n} pilot{s} behind",
    cc_sqn_sleep_titre:"Put this squadron to sleep?",
    cc_sqn_wake_titre:"Wake this squadron up?",
    cc_sqn_crest_titre:"Set this crest?",
    cc_rights_role_titre:"Change the leaders' role?",
    cc_rights_chef_titre:"Appoint the squadron leader?",
    cc_rights_chef_none_titre:"Remove the squadron leader?",
    cc_rights_conn_titre:"Remove this role from sign-in?",
    cc_camp_delete_titre:"Delete this campaign?",
    cc_esc_titre:"Update the wing?",
    cc_esc_emblem_titre:"Set this emblem?",
    cc_ref_import_titre:"Import this file?",
    cc_relances_title:"Planning reminders",
    cc_relances_none:"No pilot is behind.",
    cc_relances_last:"last answer on {date}",
    cc_relances_never:"no answer",
    cc_relances_dest:"Recipients: {names}",
    cc_relances_dest_none:"No recipient (Rights screen): no DM is sent.",
    cc_relances_refus:"DM refused by {name} on {date}",
    cc_rights_title:"Rights",
    cc_rights_role_title:"Discord role \"squadron leader\"",
    cc_rights_role_hint:"One role for the whole wing, chosen from the Discord server's role list — no ID to type in. Until it's set, only admins and deputies can enter the module, and no leader can be appointed below.",
    cc_rights_role_src:"read from the Discord server",
    cc_rights_role_none:"none",
    cc_rights_role_absent:"absent from the server",
    cc_rights_cmd_title:"Squadron command",
    cc_rights_cmd_hint_admin:"You appoint the leader, among squadron members who hold the role above, recorded at each login and each roll call. A member who was just granted the role on Discord appears after the next roll call or their next login. The deputy is appointed by you or by the squadron leader.",
    cc_rights_cmd_hint_chef:"You appoint your squadron's deputy. Everything else is an administrator's responsibility.",
    cc_rights_col_squadron:"Squadron",
    cc_rights_col_chef:"Leader",
    cc_rights_col_deputy:"Deputy",
    cc_rights_no_candidate:"no member of this squadron holds that role at the last check",
    cc_rights_pick_role_first:"choose the role above first",
    cc_rights_no_member:"no member",
    cc_rights_plan_title:"Planning event editing",
    cc_rights_plan_hint:"Who can create events. By Discord server role, or person by person. <b>Each person then edits what they created</b> — editing someone else's event is a separate right, further below.",
    cc_rights_plan_by_role:"By Discord role",
    cc_rights_plan_by_person:"By name",
    cc_rights_plan_none:"None",
    cc_rights_add:"Add",
    cc_rights_cancel:"Cancel",
    cc_rights_chip_remove:"Remove",
    cc_rights_choose:"choose",
    cc_rights_conn_title:"Application access",
    cc_rights_conn_hint:"The Discord roles that open the connection. A member with none of them can't get in. Administrators always get in, whatever their roles.",
    cc_rights_conn_effect:"A removal takes effect immediately: the person lands back on the sign-in page on their next action. Adding it back lets them straight back in.",
    cc_rights_conn_src_app:"Managed here.",
    cc_rights_debrief_title:"Access to the Wing module",
    cc_rights_debrief_hint:"Holders of these roles enter the Wing module, in addition to administrators, who always enter.",
    cc_rights_debrief_reload_hint:"A grant only takes effect on page reload — not immediately, unlike application access.",
    cc_rights_relances_title:"Planning reminders",
    cc_rights_relances_hint:"Holders of these roles and these accounts receive a Discord DM when a squadron pilot has answered no planning occurrence, neither from the last four weeks nor from the next 90 days — once, when the name is added. A newly added recipient receives the current list at once. With no recipient, no DM is sent; the list stays on the Members screen.",
    // Lot « Les relances nominatives » (R1) : the accounts row.
    cc_rights_relances_ids:"Accounts",
    cc_rights_conn_qual_chef:"appoints leaders",
    cc_rights_conn_qual_squadron:"attaches to {squadron}",
    cc_rights_conn_add:"Add a role that opens the connection",
    cc_rights_conn_confirm:"Remove <b>{role}</b> from access?",
    cc_rights_conn_confirm_impact_one:" <b>{n} known member</b> would lose their last access role and would no longer be able to enter.",
    cc_rights_conn_confirm_impact_many:" <b>{n} known members</b> would lose their last access role and would no longer be able to enter.",
    cc_rights_conn_confirm_mine:" <b>You remain admitted as an administrator, whatever this removal.</b>",
    cc_rights_conn_immediate:" The effect is <b>immediate</b>.",
    cc_rights_conn_deny_last:"Can't remove <b>{role}</b>: the list can't be emptied. Add another role first.",
    cc_rights_conn_ko:"Discord server unreachable — can't add",
    cc_rights_content_title:"Content rights",
    cc_rights_content_hint:"Four rights granted by Discord role. Administrators always have them.",
    cc_rights_content_sess_title:"Rename a mission and write the wing note",
    cc_rights_content_sess_hint:"Global scope: sessions are multi-squadron.",
    cc_rights_content_evt_title:"Edit someone else's event",
    cc_rights_content_evt_hint:"Adds to planning editing above, which only lets each person fix their own events.",
    cc_rights_content_evt_reload_hint:"A grant only takes effect on page reload — not immediately, unlike application access.",
    cc_rights_content_camp_title:"Create and edit a campaign",
    cc_rights_content_camp_hint:"One right for both actions: it's the same job on the same object.",
    cc_rights_content_campdel_title:"Delete a campaign",
    cc_rights_content_campdel_hint:"A separate right, deliberately. A campaign with missions attached cannot be deleted, no matter who holds it.",
    cc_rights_content_camp_reload_hint:"For these two rights too, a grant only takes effect when the page is reloaded.",
    cc_rights_ref_title:"Discord roles, and what they do here",
    cc_rights_ref_hint:"A reading reference, to keep roles up to date on Discord. Every member carries a role that opens access; squadron roles and the leader role are separate roles, and have no place in the access list.",
    cc_rights_ref_col_role:"Discord role",
    cc_rights_ref_col_office:"What it does here",
    cc_rights_ref_col_count:"Known members",
    cc_rights_ref_limit_hint:"The count covers members <b>known to the Ready Room</b>, based on the roles recorded at their login and at each roll call.",
    cc_rights_ref_office_none:"—",
    cc_rights_ref_office_access:"Opens access",
    cc_rights_ref_office_plan:"Edits the planning",
    cc_rights_ref_office_session:"Renames missions",
    cc_rights_ref_office_event_any:"Edits others' events",
    cc_rights_ref_office_campaign:"Creates and edits campaigns",
    cc_rights_ref_office_campaign_delete:"Deletes campaigns",
    cc_rights_ref_office_debrief:"Enters the Wing",
    cc_rights_ref_absent_note:"Role(s) referenced here but absent from the Discord server: {roles}.",
    cc_rights_partial:"No leader appointed: {squadrons}. Members of these squadrons have no one to administer them.",
    cc_rights_chef_sans_role_opt:"{name} · without the leader role",
    cc_rights_chef_sans_role:"without the leader role",
    cc_rights_partial_sans_role:"Leaders without the Discord leader role, who therefore can't enter the Command Centre: {squadrons}.",
    cc_rights_deputy_note:"Your rank: deputy of {squadron}. A squadron's leader and deputy are appointed here by an administrator; the deputy can also be appointed by the leader.",
    cc_rights_no_squadron:"You don't lead any squadron. Leaders and deputies are appointed on this screen by an administrator.",
    cc_rights_empty:"No active squadron.",
    cc_rights_error:"Unable to load rights.",
    cc_rights_retry:"Retry",
    cc_rights_confirm_chef:"Appoint {name} as leader of {squadron}?",
    cc_rights_confirm_chef_takeover:"Appoint {name} as leader of {squadron}? {previous} returns to plain member.",
    cc_rights_confirm_chef_none:"Remove {previous} from command of {squadron}? The squadron will have no leader.",
    cc_rights_confirm_role:"Confirm the Discord role for squadron leaders: {role}?",
    cc_rights_deny_last_editor:"Removal refused — last planning editor. Add another one first.",
    cc_rights_confirm_apply:"Apply",
    cc_sqn_act_edit:"Edit",
    cc_sqn_act_save:"Save",
    cc_sqn_act_sleep:"Put to sleep",
    cc_sqn_act_wake:"Wake up",
    cc_sqn_rename_effect:"The new name {new} will replace {old} everywhere in the app, including on the weekly schedule.",
    cc_sqn_tag_effect:"{old} will no longer be stripped from callsigns — {new} will be instead. Displayed names change for all squadrons, not just this one.",
    cc_sqn_sleep_confirm:"Put {squadron} to sleep? Its Discord role stops being recognised. At the next roll call or on their next login, its {count} members leave it: Free Agents if they keep access to the app, archived otherwise.",
    cc_sqn_sleep_confirm_empty:"Put {squadron} to sleep? It has no members; its Discord role stops being recognised.",
    cc_sqn_wake_pick:"Wake up {squadron}: pick the Discord role that will now attach its members.",
    cc_sqn_wake_deny:"Pick a Discord role first — without one, {squadron} would be active and attach no one.",
    cc_sqn_create_title:"Create a squadron",
    cc_sqn_create_hint:"The identifier is stripped from members' callsigns everywhere in the app — enter it exactly as it appears in their Discord names.",
    cc_sqn_create_submit:"Create",
    cc_sqn_create_deny_fields:"A squadron needs an identifier.",
    cc_sqn_create_deny_role:"This Discord role already attaches {squadron}. Two active squadrons cannot share a role.",
    cc_sqn_created:"{squadron} has been created. It will attach its members at the next roll call or on their next login.",
    cc_sqn_act_crest:"Crest…",
    cc_sqn_crest_alt:"Crest of {squadron}",
    cc_sqn_crest_none:"No crest",
    cc_sqn_crest_preview:"{dims} → squared, reduced to 512 px maximum, re-encoded as PNG.",
    cc_sqn_crest_apply:"Set the crest",
    cc_sqn_crest_done:"{squadron}'s crest is set.",
    cc_sqn_crest_deny_vector:"{name} is a vector file: it can embed executable code. PNG or WebP only, never a vector format.",
    cc_sqn_crest_deny_weight:"{name} is {size} MB. 2 MiB maximum — a crest is a flat mark, not a photograph.",
    cc_sqn_crest_deny_format:"{name} isn't a PNG or WebP image. The extension proves nothing: the server re-reads the file's first bytes.",
    cc_sqn_crest_deny_broken:"{name} is unreadable or truncated.",
    cc_campaigns_title:"Campaigns",
    cc_camp_col_name:"Campaign",
    cc_camp_col_sim:"Simulator",
    cc_camp_col_theater:"Theater",
    cc_camp_col_status:"Status",
    cc_camp_col_missions:"Missions",
    cc_camp_col_actions:"Actions",
    cc_camp_field_name_ph:"Campaign name",
    cc_camp_field_desc:"Description",
    cc_camp_status_en_cours:"Ongoing",
    cc_camp_status_close:"Closed",
    cc_camp_empty:"No campaign registered. A mission deposited without a campaign remains a normal mission — attaching one is optional.",
    cc_camp_error:"Couldn't load campaigns.",
    cc_camp_retry:"Retry",
    cc_escadre_title:"Wing",
    cc_esc_emblem_btn:"Emblem…",
    cc_esc_emblem_alt:"Emblem of {wing}",
    cc_esc_emblem_apply:"Set the emblem",
    cc_esc_emblem_done:"The emblem is set.",
    cc_esc_id_title:"Wing identity",
    cc_esc_id_hint:"What is written here replaces the wing everywhere in the application: screen subtitles, top bar, sign-in page, Discord messages, classification references.",
    cc_esc_admin_only:"Administrators only.",
    cc_esc_f_designation:"Designation",
    cc_esc_f_fullname:"Full name",
    cc_esc_f_period:"Period",
    cc_esc_f_sigle:"Code",
    cc_esc_f_tag:"Tag",
    cc_esc_h_period:"One language only: it is shown as written in French and in English alike.",
    cc_esc_h_sigle:"In classification references: “NATO RESTRICTED · {sigle}/DCS/MSN/0012”.",
    cc_esc_h_tag:"The prefix removed from the start of nicknames: “{tag} | Kodiak” shows as “Kodiak”. It follows the designation.",
    cc_esc_save:"Save",
    cc_esc_confirm:"Changes: {changes}.",
    cc_esc_change_item:"{field} “{from}” → “{to}”",
    cc_esc_confirm_tag:"The tag changes: nothing stored is rewritten, but a Discord nickname that still starts with “{old}” will keep that prefix — in the schedule, in Discord messages and in reminders — until the pilot changes it.",
    cc_esc_saved:"The wing identity is saved.",
    cc_esc_error:"Could not load the wing identity.",
    cc_ref_title:"Reference lists",
    cc_ref_hint:"The names DCS gives to units and weapons, and the name the Ready Room shows instead — in a flight's log, the tallies, accuracy, threats and the Record. A key without a label is shown as is. A type's category files its destructions in the tallies; it is automatic unless forced here.",
    cc_ref_search_ph:"Search a key or a label",
    cc_ref_sans_libelle:"No label ({n})",
    cc_ref_export:"Export",
    cc_ref_import:"Import…",
    cc_ref_types_title:"Unit types · {n}",
    cc_ref_armes_title:"Weapons · {n}",
    cc_ref_col_cle:"DCS key",
    cc_ref_col_libelle:"Label",
    cc_ref_col_categorie:"Category",
    cc_ref_modifier:"Edit",
    cc_ref_cle_affichee:"— key shown",
    cc_ref_forcee:"forced",
    cc_ref_auto:"Automatic ({cat})",
    // Lot « La plume » §6 : the target categories, in the screen language (catLabel).
    cat_avion:"Aircraft",
    cat_helicoptere:"Helicopter",
    cat_defense_aa:"Air defence",
    cat_char:"Tank",
    cat_artillerie:"Artillery",
    cat_blinde_leger:"Light armour",
    cat_infanterie:"Infantry",
    cat_vehicule:"Vehicle",
    cat_navire:"Ship",
    cat_static:"Static",
    cat_inconnu:"Unknown",
    cc_ref_import_bilan:"{fichier} — contract {contrat}, version {version}. Types: {tp} labels set, {ti} unchanged, {tc} categories forced. Weapons: {ap} labels set, {ai} unchanged. {r} refused. Nothing is deleted: a key missing from the file keeps its label.",
    cc_ref_refus_item:"“{cle}”: {raison}",
    cc_ref_import_invalide:"{fichier} is not a readable reference list: {raison}",
    cc_ref_import_done:"The reference list is imported.",
    cc_ref_saved:"“{cle}” is saved.",
    cc_ref_error:"Could not load the reference lists.",
    cc_ref_empty_filter:"No key matches.",
    // Lot « L'écran Archives du Centre » : 25 clés (écran Archives du Centre de Commandement).
    cc_arch_title:"Archives",
    cc_arch_mbr_title:"Archived members",
    cc_arch_mbr_hint:"Profiles that left the roster at roll call. Nothing is erased: their flights and missions remain, and returning on Discord brings them back at the next roll call.",
    cc_arch_col_membre:"Member",
    cc_arch_col_escadrille:"Last squadron",
    cc_arch_col_sortie:"Left",
    cc_arch_col_missions:"Missions",
    cc_arch_col_heures:"Hours",
    cc_arch_mbr_empty:"No archived member.",
    cc_arch_sav_title:"Backups",
    cc_arch_sav_hint:"A backup takes the database and the crests; files uploaded to the Wing stay with the machine backup. The last ten manual ones are kept; automatic ones follow their setting, deployment ones their own purge. Restoring is done from the command line (Installation Guide, chapter 11), never from here.",
    cc_arch_sav_btn:"Back up now",
    cc_arch_sav_busy:"Backing up…",
    cc_arch_sav_done:"Backup done: {taille}, database and crests.",
    cc_arch_col_date:"Date",
    cc_arch_col_origine:"Origin",
    cc_arch_col_revision:"Revision",
    cc_arch_col_taille:"Size",
    cc_arch_col_fichiers:"Files",
    cc_arch_origine_manuelle:"Manual",
    cc_arch_origine_deploiement:"Deployment",
    cc_arch_origine_migration:"Migration",
    // Lot « Les sauvegardes automatiques » : l'origine, le panneau de réglage, son état.
    cc_arch_origine_automatique:"Automatic",
    cc_arch_auto_title:"Automatic backup",
    cc_arch_auto_freq_0:"Off",
    cc_arch_auto_freq_h:"Every {n} h",
    cc_arch_auto_freq_168:"Every 7 days",
    cc_arch_auto_garder:"Keep the last {n}",
    cc_arch_auto_derniere:"Last: {date} · {heure}",
    cc_arch_auto_aucune:"None yet",
    cc_arch_auto_echec:"Last attempt failed ({date} · {heure}): {raison}",
    cc_arch_auto_aria_freq:"Frequency",
    cc_arch_auto_aria_garder:"Retention",
    cc_arch_dl_base:"Database",
    cc_arch_dl_ecussons:"Crests",
    cc_arch_sav_empty:"No backup.",
    cc_arch_error:"Couldn't load the archives.",
    // Lot « Polish du Centre » : le diagnostic d'accès (écran Membres) et le journal des modifications (écran Archives) — 88 clés.
    cc_diag_title:"Access check",
    cc_diag_hint:"For one member: each right, whether they hold it, and what grants it. Administrators only.",
    cc_diag_choose:"Choose a member…",
    cc_diag_roles:"Discord roles read at the last roll call or login: {roles}",
    cc_diag_roles_none:"none",
    cc_diag_col_droit:"Right",
    cc_diag_col_accorde:"Granted",
    cc_diag_col_par:"Through",
    cc_diag_oui:"Yes",
    cc_diag_non:"No",
    cc_diag_error:"Could not read this member's access.",
    cc_diag_d_app_access:"Sign in to the app",
    cc_diag_d_command_access:"Command Center",
    cc_diag_d_debrief_access:"Wing",
    cc_diag_d_event_create:"Planning — create",
    cc_diag_d_event_edit_any:"Planning — edit any",
    cc_diag_d_session_edit:"Missions — edit",
    cc_diag_d_campaign_manage:"Campaigns — manage",
    cc_diag_d_campaign_delete:"Campaigns — delete",
    cc_diag_d_relances_destinataire:"Reminders — receive",
    cc_diag_s_admin:"administrator (.env)",
    cc_diag_s_role:"role “{role}”",
    cc_diag_s_compte:"by name, Rights screen",
    cc_diag_s_adjoint:"deputy of {escadrille}",
    cc_diag_s_aucun:"none of their roles, nor their account",
    cc_lien_title:"Backup sign-in link",
    cc_lien_hint:"For a pilot the Discord sign-in cannot let in. The link opens their session once, within 24 hours. Give it to them only: anyone who opens it signs in under their name. Issuing a new one cancels the previous one.",
    cc_lien_btn:"Issue a link",
    cc_lien_copy:"Copy",
    cc_lien_copied:"Link copied",
    cc_lien_until:"Single use, valid until {date} at {heure}.",
    cc_lien_refus:"This member has no sign-in right: a link would open nothing for them.",
    cc_lien_error:"The link could not be issued.",
    cc_jr_title:"Change log",
    cc_jr_hint:"Every Command Center change: who, when, what, before and after. Most recent first. Administrators only.",
    cc_jr_col_date:"Date",
    cc_jr_col_par:"By",
    cc_jr_col_action:"Action",
    cc_jr_col_objet:"Subject",
    cc_jr_col_detail:"Detail",
    cc_jr_empty:"Nothing logged since the log was put in place.",
    cc_jr_more:"Older",
    cc_jr_error:"Could not read the log.",
    cc_jr_a_squadron_create:"Squadron created",
    cc_jr_a_squadron_edit:"Squadron edited",
    cc_jr_a_squadron_crest:"Crest set",
    cc_jr_a_squadron_sleep:"Put to sleep",
    cc_jr_a_squadron_wake:"Woken",
    cc_jr_a_squadron_leader:"Leader set",
    cc_jr_a_squadron_deputy:"Deputy set",
    cc_jr_a_campaign_create:"Campaign created",
    cc_jr_a_campaign_edit:"Campaign edited",
    cc_jr_a_campaign_delete:"Campaign deleted",
    cc_jr_a_members_appel:"Roll call",
    cc_jr_a_members_lien_secours:"Backup link issued",
    cc_jr_a_auth_lien_secours:"Backup link used",
    cc_jr_a_rights_chef_role:"Leaders' role",
    cc_jr_a_rights_event_editors:"Planning editors",
    cc_jr_a_rights_app_access:"App access",
    cc_jr_a_rights_debrief_access:"Wing access",
    cc_jr_a_rights_relances:"Reminder recipients",
    cc_jr_a_rights_content:"Content rights",
    cc_jr_a_wing_edit:"Wing edited",
    cc_jr_a_wing_emblem:"Emblem set",
    cc_jr_a_ref_type:"Type",
    cc_jr_a_ref_arme:"Weapon",
    cc_jr_a_ref_import:"Reference imported",
    cc_jr_a_archives_sauvegarde:"Manual backup",
    cc_jr_a_archives_automatique:"Automatic backup set",
    // Lot « La réception du .rrlog de l'agent » (v1.0089) : le bloc « Serveur DCS » de l'écran Archives et ses deux gestes du journal.
    cc_agent_title:"DCS server",
    cc_agent_hint:"The DCS server agent sends here the log of each session played, for the Debrief to read. It identifies itself with a token issued on this screen: only one is active at a time.",
    cc_agent_actif:"Active token, issued {date} by {nom} · {envoi}",
    cc_agent_envoi_aucun:"no upload received",
    cc_agent_envoi_le:"last upload received {date} at {heure}",
    cc_agent_aucun:"No token: the DCS server agent cannot send anything.",
    cc_agent_emettre:"Issue a token",
    cc_agent_remplacer:"Replace the token",
    cc_agent_revoquer:"Revoke",
    cc_agent_conf_remplacer_titre:"Replace the token?",
    cc_agent_conf_revoquer_titre:"Revoke the token?",
    cc_agent_conf_texte:"The old token stops working at once: the DCS server will send nothing until the new one is in its configuration.",
    cc_agent_conf_remplacer_ok:"Replace",
    cc_agent_conf_revoquer_ok:"Revoke",
    cc_agent_jeton:"Token",
    cc_agent_adresse:"Address",
    cc_agent_copie:"Copied",
    cc_agent_une_fois:"This token will never be shown again. Give it to the DCS server administrator: it goes in readyroom_envoi.json, field “jeton”, and the address in the field “adresse”.",
    cc_agent_recus:"Latest files received",
    cc_agent_col_recu:"Received",
    cc_agent_col_mission:"Mission",
    cc_agent_col_theatre:"Theatre",
    cc_agent_col_date:"Mission date",
    cc_agent_col_taille:"Size",
    cc_agent_col_etat:"Status",
    cc_agent_etat_attente:"Awaiting reading",
    cc_agent_vide:"No file received from the DCS server.",
    cc_jr_a_agent_jeton_emis:"DCS server token issued",
    cc_jr_a_agent_jeton_revoque:"DCS server token revoked",
    // Lot « L'accès invité » (v1.0070): the strip, the wall, the Rights-screen block and the journal.
    invite_bandeau:"Guest access · read-only demonstration — until {date}",
    invite_lecture_seule:"Guest access: read only.",
    cc_inv_title:"Guests — demonstration",
    cc_inv_hint:"Someone outside the wing's Discord server, allowed in by their Discord ID, to show them the Ready Room. They see everything a leader sees, <b>strictly read-only</b>, and appear in no table. They sign in with \"Sign in with Discord\".",
    cc_inv_hint_duree:"Thirty days, renewable. A revocation takes effect at their next action.",
    cc_inv_id_label:"Discord ID",
    cc_inv_verifier:"Check",
    cc_inv_compte:"Discord account: <b>{nom}</b> (@{username}) ·",
    cc_inv_inviter:"Invite for 30 days",
    cc_inv_col_invite:"Guest",
    cc_inv_col_id:"ID",
    cc_inv_col_par:"Invited by",
    cc_inv_col_jusqua:"Until",
    cc_inv_col_entree:"Last sign-in",
    cc_inv_prolonger:"Extend by 30 days",
    cc_inv_revoquer:"Revoke",
    cc_inv_vide:"No guests.",
    cc_inv_jamais:"never",
    cc_jr_a_invites_ajout:"Guest added",
    cc_jr_a_invites_prolongation:"Guest access extended",
    cc_jr_a_invites_revocation:"Guest access revoked",
    cc_jr_a_invites_entree:"Guest signed in",
    // Lot « Le rattachement des dépôts » (v1.0052): the two Debrief gestures; “File” reuses cc_jr_f_fichier.
    cc_jr_a_debrief_deplacer:"Mission file moved",
    cc_jr_a_debrief_fusionner:"Missions merged",
    cc_jr_f_mission:"Mission",
    cc_jr_f_absorbee:"Merged mission",
    cc_jr_f_designation:"Designation",
    cc_jr_f_callsign:"Callsign",
    cc_jr_f_full_name:"Full name",
    cc_jr_f_discord_role_id:"Discord role",
    cc_jr_f_aircraft:"Aircraft",
    cc_jr_f_liveries:"Liveries",
    cc_jr_f_default_liveries:"Default liveries",
    cc_jr_f_nickname:"Nickname",
    cc_jr_f_name:"Name",
    cc_jr_f_sim:"Simulator",
    cc_jr_f_map_name:"Theater",
    cc_jr_f_status:"Status",
    cc_jr_f_description:"Description",
    cc_jr_f_entres:"Joined",
    cc_jr_f_sortis:"Left",
    cc_jr_f_role_id:"Role",
    cc_jr_f_profile_id:"Member",
    cc_jr_f_role_ids:"Roles",
    cc_jr_f_profile_ids:"Accounts",
    cc_jr_f_session_edit_role_ids:"Missions — edit",
    cc_jr_f_event_edit_any_role_ids:"Planning — edit any",
    cc_jr_f_campaign_manage_role_ids:"Campaigns — manage",
    cc_jr_f_campaign_delete_role_ids:"Campaigns — delete",
    cc_jr_f_period:"Period",
    cc_jr_f_sigle:"Abbreviation",
    cc_jr_f_tag:"Tag",
    cc_jr_f_libelle:"Label",
    cc_jr_f_categorie:"Category",
    cc_jr_f_poses:"Applied",
    cc_jr_f_refuses:"Rejected",
    cc_jr_f_fichier:"File",
    cc_jr_f_intervalle_h:"Frequency (h)",
    cc_jr_f_garder:"Retention",
    // Lot « La page Configuration du Centre » (v1.0106) : l'onglet, ses deux blocs et les trois actions du journal.
    nav_cc_configuration:"Config",
    cc_cfg_title:"Configuration",
    cc_cfg_hint:"Server settings, kept by the Ready Room. Administrators only; every change is recorded in the Archives log.",
    cc_cfg_error:"Unable to load the configuration.",
    cc_cfg_adm_title:"Administrators",
    cc_cfg_adm_hint:"An administrator opens the whole Command Center, backups, invitations and emergency links. Founders are set on the server; the others are appointed here.",
    cc_cfg_adm_col_nom:"Member",
    cc_cfg_adm_col_statut:"Status",
    cc_cfg_adm_col_depuis:"Appointed on",
    cc_cfg_adm_fondateur:"Founder",
    cc_cfg_adm_nomme:"Appointed",
    cc_cfg_adm_fondateur_note:"Changed on the server",
    cc_cfg_adm_inconnu:"Account {id}",
    cc_cfg_adm_choisir:"Choose a member",
    cc_cfg_adm_nommer:"Appoint",
    cc_cfg_adm_retirer:"Remove",
    cc_cfg_adm_nommer_titre:"Appoint as administrator",
    cc_cfg_adm_nommer_texte:"{nom} will be able to change everything in the Command Center, this page included, and appoint or remove other administrators.",
    cc_cfg_adm_retirer_titre:"Remove an administrator",
    cc_cfg_adm_retirer_texte:"{nom} loses administrator rights; the rights given by their roles remain.",
    cc_cfg_adm_retirer_soi:"You are removing your own administrator rights: the page will reload without the Configuration.",
    cc_cfg_reg_title:"Server settings",
    cc_cfg_cle_absente:"The server encryption key (CONFIG_KEY) is missing or invalid: secrets can be neither read nor saved. The other settings can still be changed.",
    cc_cfg_col_reglage:"Setting",
    cc_cfg_col_valeur:"Value",
    cc_cfg_col_action:"Action",
    cc_cfg_g_recit:"Mission report narrative",
    cc_cfg_g_digest:"Discord — digest",
    cc_cfg_g_reponses:"Discord — replies",
    cc_cfg_g_tuiles:"Map tiles",
    cc_cfg_g_suites:"Suites (Mission Plan)",
    cc_cfg_g_fuseau:"Time zone",
    cc_cfg_l_REFERENCE_TZ:"Wing time zone",
    cc_cfg_h_REFERENCE_TZ:"The time zone in which the Ready Room sorts days, unrolls series, writes the times of Discord messages and reports, and runs its 6 a.m. pass. A name from the time zone database, such as Europe/Paris or America/New_York. Set it at installation: a change recalculates nothing, and series then follow the new zone's daylight saving time.",
    cc_cfg_l_ANTHROPIC_API_KEY:"Anthropic API key",
    cc_cfg_h_ANTHROPIC_API_KEY:"Used to write the mission report narrative. Without a key, or without credit, the narrative is not written.",
    cc_cfg_l_ANTHROPIC_MODEL:"Writing model",
    cc_cfg_h_ANTHROPIC_MODEL:"The identifier of the model that writes the narrative. Empty: the narrative is not written.",
    cc_cfg_l_ANTHROPIC_EFFORT:"Writing effort",
    cc_cfg_h_ANTHROPIC_EFFORT:"The higher the effort, the more the writing reasons, and the slower and costlier it gets. “Medium” is the proven setting.",
    cc_cfg_effort_low:"Low",
    cc_cfg_effort_medium:"Medium",
    cc_cfg_effort_high:"High",
    cc_cfg_effort_xhigh:"Very high",
    cc_cfg_effort_max:"Maximum",
    cc_cfg_modele_choisir:"Choose a model",
    cc_cfg_modele_hors_liste:"(not in the list)",
    cc_cfg_modeles_source:"Anthropic's active models, read with the API key.",
    cc_cfg_modeles_sans_cle:"Without an API key, the model list is unavailable: type the model identifier.",
    cc_cfg_modeles_erreur:"Anthropic did not answer: the model list is unavailable, type the model identifier.",
    cc_cfg_modeles_detail:"Reason: {detail}",
    cc_cfg_effort_incompatible:"This model does not accept the “{effort}” effort: choose another effort first.",
    cc_cfg_l_DISCORD_WEBHOOK_URL:"Digest webhook URL",
    cc_cfg_h_DISCORD_WEBHOOK_URL:"The Discord channel that receives the weekly schedule. The address grants access, so it is kept secret. Empty: nothing is posted.",
    cc_cfg_l_DISCORD_DIGEST_LOCALE:"Digest language",
    cc_cfg_h_DISCORD_DIGEST_LOCALE:"The language of the digest messages in Discord.",
    cc_cfg_l_DISCORD_DIGEST_TOKEN:"Manual update token",
    cc_cfg_h_DISCORD_DIGEST_TOKEN:"Protects Discord message updates started by hand or by a script. Empty: they are refused; the 6 a.m. update does not need it.",
    cc_cfg_l_DISCORD_RSVP_ENABLED:"Replies in Discord",
    cc_cfg_h_DISCORD_RSVP_ENABLED:"Members answer events from Discord, with the bot's buttons. Off: the bot sleeps and only the digest is posted.",
    cc_cfg_l_DISCORD_BOT_TOKEN:"Bot token",
    cc_cfg_h_DISCORD_BOT_TOKEN:"The token of the Ready Room's Discord bot (Discord developer portal). Do not clear it when turning replies off: the bot needs it to remove its messages.",
    cc_cfg_l_DISCORD_PUBLIC_KEY:"Application public key",
    cc_cfg_h_DISCORD_PUBLIC_KEY:"64 hexadecimal characters, from the Discord developer portal. It checks the buttons and the /readyroom command.",
    cc_cfg_l_DISCORD_NOTIFY_CHANNEL_ID:"Replies channel",
    cc_cfg_h_DISCORD_NOTIFY_CHANNEL_ID:"The identifier of the channel where the bot posts events (17 to 20 digits).",
    cc_cfg_l_DISCORD_RSVP_HORIZON_DAYS:"Replies horizon (days)",
    cc_cfg_h_DISCORD_RSVP_HORIZON_DAYS:"Only events in the coming days get a message, from 1 to 120 days.",
    cc_cfg_l_TILES_UPSTREAM:"Tile server",
    cc_cfg_h_TILES_UPSTREAM:"The server queried when a map tile is neither in the mirror nor in the cache. https:// only.",
    cc_cfg_l_WING_ID:"Wing key",
    cc_cfg_h_WING_ID:"The key under which Mission Plan and HQ store the wing's settings in members' browsers. Empty: taken from the designation, spaces turned into hyphens. Changing it loses those settings. Letters, digits, “.”, “_” and “-”, at most 64 characters, starting with a letter or a digit.",
    cc_cfg_s_rempli:"Set",
    cc_cfg_s_vide:"Empty",
    cc_cfg_s_remplace:"Replaced",
    cc_cfg_s_illisible:"Unreadable — enter it again",
    cc_cfg_s_modifie:"Changed on {date} by {nom}",
    cc_cfg_s_repris:"Imported from the server on {date}",
    cc_cfg_saisir:"Enter",
    cc_cfg_remplacer:"Replace",
    cc_cfg_vider:"Clear",
    cc_cfg_enregistrer:"Save",
    cc_cfg_defaut:"Reset to default",
    cc_cfg_defaut_val:"Default: {v}",
    cc_cfg_defaut_aucun:"Default: none",
    cc_cfg_oui:"On",
    cc_cfg_non:"Off",
    cc_cfg_lang_fr:"French",
    cc_cfg_lang_en:"English",
    cc_cfg_vider_titre:"Clear this secret",
    cc_cfg_vider_texte:"“{reglage}” will be erased from the server; what depends on it stops until it is entered again.",
    cc_cfg_err_valeur:"Value refused: check its format.",
    cc_cfg_err_cle:"Encryption key missing: this secret cannot be saved.",
    cc_cfg_enregistre:"Saved.",
    cc_cfg_dos_title:"Server folders",
    cc_cfg_dos_hint:"Plugged in by Docker at startup, from the server's .env file. Read-only: they are changed on the server and take effect at the next restart.",
    cc_cfg_dos_col_dossier:"Folder",
    cc_cfg_dos_col_contenu:"Content",
    cc_cfg_dos_l_suites:"The suites",
    cc_cfg_dos_h_suites:"The Mission Plan and Mission Tools files the Ready Room serves to the wing.",
    cc_cfg_dos_l_tuiles:"DCS map tiles",
    cc_cfg_dos_h_tuiles:"The DCS Olympus archives extracted on the server.",
    cc_cfg_dos_l_tuiles_gardees:"Kept tiles",
    cc_cfg_dos_h_tuiles_gardees:"Tiles fetched from Olympus and kept by the Ready Room; this folder fills itself.",
    cc_cfg_dos_un:"1 file",
    cc_cfg_dos_n:"{n} files",
    cc_cfg_dos_plafond:"{n} files or more",
    cc_cfg_dos_vide:"Empty",
    cc_cfg_dos_vide_aide:"No files: the {variable} line of .env is missing, or points to an empty folder.",
    cc_cfg_dos_vide_aide_tuiles_gardees:"No kept tiles yet: the folder fills as the map is used.",
    cc_cfg_dos_absent:"Not found",
    cc_cfg_dos_absent_aide:"The folder {chemin} does not exist in the container: see docker-compose.yml.",
    cc_cfg_dos_erreur:"Could not read the server folders.",
    cc_jr_a_reglage_edit:"Setting changed",
    cc_jr_a_admin_nommer:"Administrator appointed",
    cc_jr_a_admin_retirer:"Administrator removed",
    cc_jr_f_valeur:"Value",
    cc_camp_act_edit:"Edit",
    cc_camp_act_delete:"Delete",
    cc_camp_create_title:"Create a campaign",
    cc_camp_create_hint:"Only the name is required. Two campaigns can't share the same name on the same simulator — case doesn't matter.",
    cc_camp_edit_title:"Edit \"{name}\"",
    cc_camp_edit_hint:"The name stays unique per simulator. Switching the status to \"Closed\" erases nothing: the campaign and its missions remain visible.",
    cc_camp_field_desc_ph:"Description — will appear on the Wing module's Campaigns screen",
    cc_camp_submit_create:"Create",
    cc_camp_submit_save:"Save",
    cc_camp_create_deny_name:"A campaign name is required.",
    cc_camp_sim_locked:"The simulator can no longer be changed: {count} missions are attached to this campaign. Moving them to another simulator would make them invisible in selectors. The field is locked, not hidden.",
    cc_camp_delete_confirm:"Delete {name}? No mission is attached to it. The effect is immediate and permanent.",
    cc_camp_delete_deny:"Can't delete {name}: {count} missions are attached to it. A campaign that has been used isn't erased — it's closed, and remains visible. To delete it anyway, detach its missions first from session editing.",
    cc_camp_note_close:"Close",
    slip_hd_title:"Desk annotation",
    slip_hd_who:"Command staff only",
    slip_select_label:"This flight is a wing member",
    slip_select_placeholder:"— choose —",
    slip_select_no_squadron:"No squadron",
    slip_memo:"The name {segment} will be retained for {who}. Their next flights under this name will be attached without you coming back here.",
    slip_cancel:"Cancel",
    slip_attach:"Attach",
    slip_attach_error:"Choose a member before attaching.",
    slip_attach_done:"Flight attached ✓",
    slip_attach_fail:"Attachment failed.",
    slip_done_alias:"Attached to {who} by a retained name, from the callsign {callsign}.",
    slip_done_engine:"Attached to {who} by the engine, from the callsign {callsign}.",
    slip_done_manual:"Attached to {who} by hand.",
    slip_correct:"Correct",
    slip_detach:"Detach",
    slip_detach_running:"Detaching…",
    slip_detach_done:"Flight detached ✓",
    slip_detach_fail:"Detachment failed.",
    slip_forget:"Forget this name",
    slip_forget_running:"Forgetting…",
    slip_forget_done:"Name forgotten ✓",
    slip_forget_fail:"Failed to forget the name.",
  }
};

const MONTHS = {
  fr:["Janvier","Février","Mars","Avril","Mai","Juin","Juillet","Août","Septembre","Octobre","Novembre","Décembre"],
  en:["January","February","March","April","May","June","July","August","September","October","November","December"]
};
// Lot D2③ : abréviations pour .sc-date (carte Missions). Un slice(0,3) naïf
// de MONTHS collisionnerait Juin/Juillet ("Jui"/"Jui") -- table dédiée.
const MONTHS_ABBR = {
  fr:["Jan","Fév","Mar","Avr","Mai","Juin","Juil","Août","Sept","Oct","Nov","Déc"],
  en:["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"]
};
const WEEKDAYS = {
  fr:["Lun","Mar","Mer","Jeu","Ven","Sam","Dim"],
  en:["Mon","Tue","Wed","Thu","Fri","Sat","Sun"]
};
/* Lot R3 §B1 : noms de jour en toutes lettres, pour l'en-tête "bloc-notes"
   de la modale Jour (WEEKDAYS ci-dessus reste l'abrégé utilisé ailleurs). */
const WEEKDAYS_FULL = {
  fr:["Lundi","Mardi","Mercredi","Jeudi","Vendredi","Samedi","Dimanche"],
  en:["Monday","Tuesday","Wednesday","Thursday","Friday","Saturday","Sunday"]
};

/* ---------- État ---------- */
let ME = null;                       // {id, name, avatar_hash, lang, squadron, capabilities}
// v0.36 : horodatage de la visite PRÉCÉDENTE (posé une fois au bootstrap,
// figé pour toute la session -> les tags "NOUVEAU" restent visibles toute
// la visite et disparaissent à la suivante). null = pas de tag (1re visite
// du compte, ou réponse /api/seen indisponible).
let SINCE = null;
let PROFILES = new Map();            // profile_id (str) -> {id, name, avatar_hash, squadron} — annuaire (via /api/hebdo)
let CURRENT_SESSION_ID = null;        // Lot D2③ §B.5 : session ouverte en vue Session (contenu réel = lot ④)
let CURRENT_SESSION = null;           // Lot D2④ : détail complet (GET /sessions/{id}), caché tant que CURRENT_SESSION_ID ne change pas
let sessionDetailLoadState = "idle";  // idle | loading | ready | error
let sessionEditOpen = false;          // Lot 2.1 §4.8b : dépli du bloc d'édition nom/note sur l'écran Session
// Lot « Le rattachement des dépôts » (v1.0052) : le fichier dont le panneau de déplacement est ouvert (un seul à la
// fois), et la fusion choisie dans « Modifier » (id de la mission, et si sa confirmation est affichée).
let sessionMoveUploadId = null;
let sessionMergeChoice = "";
let sessionMergeConfirm = false;
let sessionDetailError = null;
let CURRENT_FLIGHT_ID = null;         // Lot D2④ : vol ouvert (contenu réel = lot ⑤)
let CURRENT_FLIGHT = null;            // Lot D2⑤ : détail complet (GET .../flights/{id}), caché tant que CURRENT_FLIGHT_ID ne change pas
let flightDetailLoadState = "idle";   // idle | loading | ready | error
let flightDetailError = null;
let identifyFlightOpen = false;       // Lot « Le nom qu'on retient » v0.9917 : bascule "Corriger" (pertinent seulement si le vol est déjà rattaché -- pour un vol non rattaché le panneau est toujours affiché, cf. slipHtml())
let slipSelectedProfileId = null;     // sélection en cours du <select> du bordereau (édition) -- null = pas encore touché par l'utilisateur, "" = explicitement vidé
let DEBRIEF_MEMBERS = null;           // annuaire du bordereau (GET /api/debrief/members), cache, admin uniquement
let debriefMembersLoadState = "idle"; // idle | loading | ready | error
let reportMode = "narrative";         // Lot D2⑤ : "narrative" | "raw" -- toggle de la modale Rapport
// Lot R2 §5 : état du rapport RÉDIGÉ (Récit LLM, figé en base) -- distinct
// de CURRENT_SESSION.flights (Brut, toujours calculé côté client, inchangé
// depuis D2⑤). `null` = pas encore chargé (GET en cours ou modale fermée).
let REPORT_DATA = null;
let reportGenBusy = false;            // POST /report en cours -- désactive le bouton
let reportGenError = null;            // dernier message d'échec de rédaction, ou null
let currentLang = "fr";
let currentTheme = "dark";
let currentView = "month";           // month | week (La Planche)
let currentAppView = "planche";      // planche | hebdo (nav topbar)
let calYear = 2026, calMonth = 6;
let TODAY = {y:2026,m:6,d:5};
let activeFilters = new Set(["entrainement","mission","campagne","jeulibre"]);
let agendaScope = localStorage.getItem("agenda_scope_v1") || "upcoming"; // "upcoming" | "all"

// Lot 6 : preferences RSVP (appareils + types de mission) de l'occurrence
// actuellement ouverte dans la modale. `currentYourState` reflete l'etat
// RSVP courant de l'utilisateur (present/maybe/absent/null) -- necessaire
// pour re-soumettre le PUT /api/presences complet quand seules les
// preferences changent (le state est un champ obligatoire de l'API).
let prefsAircraft = [];
let prefsMissionTypes = [];
let currentYourState = null;
let rsvpPrefsVisible = false;

let occurrencesByDate = new Map();   // occ_date -> [Occurrence, ...]
let currentRangeFrom = null, currentRangeTo = null; // Date JS de la fenêtre actuellement affichée/fetchée

let hebdoData = null;                // dernière réponse /api/hebdo
let hebdoAnchor = null;               // ISO date, fixé au chargement (aujourd'hui)
// Lot 4 §4 : `hebdoData` peut devenir périmé pendant que l'onglet Hebdo
// n'est pas affiché (invalidate reçu pendant qu'on est sur la Planche).
// On le marque "stale" plutôt que de le refetch à l'aveugle, et on force
// un refresh au moment où l'utilisateur BASCULE vers l'onglet Hebdo — cf.
// switchAppView(). Vrai à l'init : rien n'a encore été chargé.
let hebdoStale = true;

// Lot « La Planche d'abord, la fiche qui répond » (v1.0074) : jamais nul — la Planche ouverte avant la fin de
// l'initialisation lit `weekAnchor` (`getDay`) ; l'initialisation le repose sur le vrai jour d'aujourd'hui.
let weekAnchor = new Date(TODAY.y, TODAY.m, TODAY.d);   // Date JS : jour de référence pour la vue Semaine (navigable, Lot 4 §2)

let currentModalEventId = null;
let currentModalOccDate = null;
let currentModalMode = null;         // 'view' | 'create' | 'edit' | 'day'
let currentModalOccurrence = null;   // occurrence effective (mode view/edit)
let pendingEditScope = "series";
let currentDayDate = null;           // Lot C : date affichée par la modale "day" (garde anti-course)

let eventSource = null;
let pendingRefetch = { events:false, presences:false, lastEventId:null, lastOccDate:null, report:false, lastReportSessionId:null };
let refetchTimer = null;
const DEBOUNCE_MS = 350;

/* ---------- Débrief : Missions + Déposer (Lot D2③) ---------- */
let DEBRIEF_SESSIONS = null;          // cache GET /api/debrief/sessions -> array (null = jamais chargé)
// Lot 2.3 §4.8 : cache GET /api/debrief/campaigns -> array (null = jamais
// chargé). Aucun écran neuf (§7, G1) : sert uniquement le menu déroulant de
// la modale Déposer et le sélecteur du panneau d'édition de session.
let DEBRIEF_CAMPAIGNS = null;
let missionsLoadState = "idle";       // idle | loading | error | ready
let missionsError = null;
let missionsFilters = { sim: null, squadron: "all", year: "all", month: "all" }; // Lot « Déposer depuis la barre du haut » : month « 01 »…« 12 », dans l'année choisie
let deposerQueue = [];                // [{id, file, kind, status, error}]
let deposerPhase = "select";          // select | done
let deposerBusy = false;

const WEEKDAY_KEYS = [0,1,2,3,4,5,6];

/* ---------- Helpers ---------- */
const $ = (sel,root)=> (root||document).querySelector(sel);
const $$ = (sel,root)=> Array.from((root||document).querySelectorAll(sel));

function t(key){
  const v = I18N[currentLang][key] || key;
  // Lot « L'écran Escadre du Centre » : `{wing}` = la désignation courante de l'escadre.
  return v.indexOf("{wing}") === -1 ? v : v.split("{wing}").join(wingDesignation());
}
function typeLabel(type){ return t("type_"+type); }

/* ---------- Identité de l'escadre (lot « L'écran Escadre du Centre ») ----------
   `ME.wing` (`/api/me`) est la SEULE source du front ; `applyWingIdentity()` la pose partout et
   se rejoue après `loadMe()` et après chaque écriture du Centre. Sans ligne `wing` (`ME.wing`
   nul), repli sur cette constante et sur le logo statique : la seule occurrence du littéral. */
const WING_FALLBACK = "Ready Room";
const WING_STATIC_EMBLEM = "/static/assets/img/emblem-default.png";
let WING = null;

function wingDesignation(){ return (WING && WING.designation) || WING_FALLBACK; }
function wingEmblemUrl(sha){ return sha ? `/api/wing/emblem?v=${encodeURIComponent(sha)}` : WING_STATIC_EMBLEM; }
function wingEmblemSrc(){ return wingEmblemUrl(WING && WING.emblem_sha); }

// « NATO RESTRICTED · {sigle}/DCS/{suite} », ou « NATO RESTRICTED · DCS/{suite} » sans sigle.
function mrefText(suite){
  const sigle = WING && WING.sigle;
  return "NATO RESTRICTED · " + (sigle ? sigle + "/" : "") + "DCS/" + suite;
}

function applyWingIdentity(relang){
  WING = (ME && ME.wing) || null;
  const d = wingDesignation();
  const src = wingEmblemSrc();
  $$(".landing-logo, .topbar-logo").forEach(img=>{
    img.setAttribute("alt", d);
    img.setAttribute("src", src);
    img.setAttribute("data-wing-emblem", "");
  });
  $$(".es-logo, .og-top img").forEach(img=>{
    img.setAttribute("src", src);
    img.setAttribute("data-wing-emblem", "");
  });
  const eyebrow = $(".landing-eyebrow");
  if(eyebrow) eyebrow.textContent = (WING && WING.full_name) || "";
  const foot = $(".app-footer");
  if(foot) foot.textContent = `DCS Squadron Ready Room · ${d}`;
  $$("[data-mref]").forEach(el=>{ el.textContent = mrefText(el.dataset.mref); });
  // Les clés i18n portent `{wing}` : la langue se rejoue (sauf au démarrage, où init() la pose après).
  if(relang !== false) setLang(currentLang);
  updateSessionMref();
  updateFlightMref();
}


// v0.36 : un occ est "nouveau" si son Event parent a été créé après la
// dernière visite (SINCE, figé pour la session). SINCE=null (1re visite du
// compte, ou /api/seen en échec) -> jamais de tag, occ.created_at manquant
// (payload periné avant refresh) -> jamais de tag non plus (garde-fou).
function isNewOcc(occ){ return !!(SINCE && occ && occ.created_at && new Date(occ.created_at) > SINCE); }
function newTag(occ){ return isNewOcc(occ) ? `<span class="new-tag">${t('new_tag')}</span>` : ""; }
// Lot « Ma réponse sur la Planche » (v1.0073, ARU-20) : la réponse du pilote connecté, en pastille.
// Un invité n'a pas de réponse ; sans réponse, une occurrence à venir est « à répondre », une passée n'a rien.
function monEtat(occ){
  if(estInviteEcran() || !occ || !("my_state" in occ)) return null;
  if(occ.my_state) return occ.my_state;
  return new Date(occ.start_at_utc) > new Date() ? "todo" : null;
}
function maPastille(occ){
  const etat = monEtat(occ);
  if(!etat) return "";
  const lib = etat==="todo" ? t('to_answer') : t('rsvp_'+etat);
  return `<span class="mr-pip pip-${etat}" title="${escapeAttr(t('my_answer'))} : ${escapeAttr(lib)}">${pip(etat)}</span>`;
}
function newDot(occ){
  return isNewOcc(occ) ? `<span class="new-dot" title="${escapeAttr(t('new_tag'))}" aria-label="${escapeAttr(t('new_tag'))}"></span>` : "";
}
// Lot v0.44 : jauge de présence en chaîne HTML (hebdo -- matrice + carte).
// Correctif R6.1 §1/§2 : R6 avait inversé les rendus mois/hebdo (question
// ambiguë du CdP) -- la maquette montre une BARRE empilée + chiffres en
// hebdo (ci-dessous), et des COMPTEURS seuls au mois (cf. renderCalGrid,
// classes .cal-presence/.cp-*). Classe dédiée .hgauge* pour NE PAS toucher
// .presence-gauge (mois, barre créée en JS, remplacée par le Volet B).
// Rendue uniquement si present+maybe+absent > 0 (brief §4).
function presenceGaugeHtml(counts){
  const present = counts?.present||0, maybe = counts?.maybe||0, absent = counts?.absent||0;
  if(present+maybe+absent === 0) return "";
  return `<div class="hgauge">
      <div class="hgauge-bar" title="✓ ${present} · ~ ${maybe} · ✕ ${absent}">
        ${present ? `<span class="pgb present" style="flex:${present}"></span>` : ""}
        ${maybe ? `<span class="pgb maybe" style="flex:${maybe}"></span>` : ""}
        ${absent ? `<span class="pgb absent" style="flex:${absent}"></span>` : ""}
      </div>
      <div class="hgauge-nums">
        <b class="pg-present">${present}</b> · <span class="pg-maybe">${maybe}</span> · <span class="pg-absent">${absent}</span>
      </div>
    </div>`;
}
function initials(name){ return (name||"?").slice(0,2).toUpperCase(); }
function pad2(n){ return String(n).padStart(2,"0"); }
function toISODate(d){ return `${d.getFullYear()}-${pad2(d.getMonth()+1)}-${pad2(d.getDate())}`; }

function escapeHtml(s){ const d=document.createElement("div"); d.textContent = s==null? "": String(s); return d.innerHTML; }
function escapeAttr(s){ return escapeHtml(s).replaceAll('"','&quot;'); }

/* ---------- Lot « Les référentiels : types et armes » : les libellés ----------
   `LIBELLES` : les noms que l'écran Référentiels du Centre a posés, chargés
   par `GET /api/referentiels/libelles` après `loadMe()` et relus après chaque
   écriture du référentiel. `libType`/`libArme` rendent le libellé quand il
   existe, la clé brute sinon ; `libTypeHtml`/`libArmeHtml` rendent le texte
   ÉCHAPPÉ, dans un `<span title="{clé}">` quand le libellé diffère de la clé
   (au survol, la clé brute). Tout endroit qui affiche une clé DCS de type ou
   d'arme passe par elles ; restent sur la clé brute : les silhouettes, les
   attributs de données, les listes du Centre, le panneau « Noms d'arme à
   vérifier » et tout ce que le serveur envoie au récit. */
let LIBELLES = {types: Object.create(null), armes: Object.create(null)};
function libellePour(table, cle){
  if(cle == null || cle === "") return null;
  return table[cle] || null;
}
function libType(cle){ return libellePour(LIBELLES.types, cle) || cle; }
function libArme(cle){ return libellePour(LIBELLES.armes, cle) || cle; }
function libHtml(lib, cle){
  if(cle == null) return "";
  return lib !== cle ? `<span title="${escapeAttr(cle)}">${escapeHtml(lib)}</span>` : escapeHtml(cle);
}
function libTypeHtml(cle){ return libHtml(libType(cle), cle); }
// Appareil d'un vol : le libellé échappé, ou « — » sans type.
function acTypeHtml(cle){ return cle ? libTypeHtml(cle) : "—"; }
function libArmeHtml(cle){ return libHtml(libArme(cle), cle); }
async function loadLibelles(){
  try {
    const d = await apiFetch("/api/referentiels/libelles");
    LIBELLES = {
      types: Object.assign(Object.create(null), (d && d.types) || {}),
      armes: Object.assign(Object.create(null), (d && d.armes) || {}),
    };
  } catch(e){ /* sans libellés : les clés brutes s'affichent, rien ne casse */ }
}

function avatarUrl(id, hash){
  if(!hash) return null;
  return `https://cdn.discordapp.com/avatars/${id}/${hash}.png?size=64`;
}
/* v0.76 -- Fix robustesse : un bloqueur de contenu (Brave, etc.) qui
   coupe la requête cdn.discordapp.com ne laissait auparavant aucun repli
   (le dégradé nu de .avatar restait visible). `data-avatar-fallback`
   porte les initiales pré-calculées ; la délégation globale posée une
   seule fois à l'init (cf. §4c du brief, capture sur "error") les affiche
   dans le conteneur parent si l'<img> échoue. Aucun handler inline
   (onerror=) : le codebase n'en contient aucun, une CSP future les
   casserait silencieusement. */
function avatarHtml(id, hash, name){
  const url = avatarUrl(id, hash);
  const init = initials(name);
  if(url) return `<img src="${url}" alt="" referrerpolicy="no-referrer" data-avatar-fallback="${escapeAttr(init)}">`; // Correctif R6 §5c : centrage géré par .avatar img (CSS)
  return escapeHtml(init);
}

/* Construit un ISO 8601 avec l'offset LOCAL du navigateur pour cette date
   précise (gère le DST correctement, comme zoneinfo côté backend) — cf.
   brief §"Créer / éditer" : date + heure -> ISO avec fuseau. */
function toISOStringWithOffset(d){
  const offsetMin = -d.getTimezoneOffset();
  const sign = offsetMin >= 0 ? "+" : "-";
  const abs = Math.abs(offsetMin);
  const oh = pad2(Math.floor(abs/60)), om = pad2(abs%60);
  return `${d.getFullYear()}-${pad2(d.getMonth()+1)}-${pad2(d.getDate())}T${pad2(d.getHours())}:${pad2(d.getMinutes())}:${pad2(d.getSeconds())}${sign}${oh}:${om}`;
}

function fmtLocalTime(isoUtc){
  return new Date(isoUtc).toLocaleTimeString(currentLang==="fr"?"fr-FR":"en-GB", {hour:"2-digit", minute:"2-digit"});
}
// Lot 3.2c §6.5 : miroir exact de fmtLocalTime, servira toutes les
// colonnes de date à venir du module Commandement.
function fmtLocalDate(isoUtc){
  return new Date(isoUtc).toLocaleDateString(currentLang==="fr"?"fr-FR":"en-GB", {day:"2-digit", month:"short", year:"numeric"});
}
// Lot « rr-fuseau-reglage » (v1.0120) : le fuseau réglé de l'escadre (`GET /api/me`, clé `fuseau`) ; Europe/Paris sans lui.
// Le navigateur doit accepter le nom (`Intl.DateTimeFormat` lève `RangeError` sinon) : sinon Europe/Paris. L'essai ne se refait
// pas pour une même valeur.
let fuseauEssai = {nom: null, ok: "Europe/Paris"};
function fuseauEscadre(){
  const nom = ME && ME.fuseau;
  if(!nom) return "Europe/Paris";
  if(fuseauEssai.nom !== nom){
    let ok = nom;
    try { new Intl.DateTimeFormat("en-CA", {timeZone: nom}); } catch(e){ ok = "Europe/Paris"; }
    fuseauEssai = {nom, ok};
  }
  return fuseauEssai.ok;
}

function fmtParisTime(isoUtc){
  return new Date(isoUtc).toLocaleTimeString(currentLang==="fr"?"fr-FR":"en-GB", {hour:"2-digit", minute:"2-digit", timeZone:fuseauEscadre()});
}

function creatorName(profileId){
  const key = String(profileId);
  if(ME && key === String(ME.id)) return callsign(ME.name);
  const p = PROFILES.get(key);
  return p ? callsign(p.name) : key;
}

/* ---------- Appels API ---------- */
// Lot « L'accès invité » (R11) : l'invité ne fait que lire. Un appel d'écriture ne part pas :
// l'écran montre UNE fois le toast `invite_lecture_seule`, puis l'appel échoue avec ce même
// texte pour message. Les gestes d'écriture existants montrent leur propre échec dans un
// `catch` -- par `showToast` (réduit au silence tant que dure le tour d'événements du refus :
// `inviteGarde`) ou par leur zone de note, qui lit `e.message` (le même texte). L'état affiché
// ne change pas.
let inviteGarde = false;
function refuserEcritureInvite(){
  showToast(t("invite_lecture_seule"));
  inviteGarde = true;
  setTimeout(()=>{ inviteGarde = false; }, 0);
  const err = new Error(t("invite_lecture_seule"));
  err.status = 403;
  err.invite = true;
  return err;
}
function estInviteEcran(){ return !!(ME && ME.invite); }

async function apiFetch(path, opts){
  if(estInviteEcran() && String((opts && opts.method) || "GET").toUpperCase() !== "GET"){
    throw refuserEcritureInvite();
  }
  const res = await fetch(path, Object.assign({credentials:"same-origin"}, opts||{}));
  if(res.status === 401){
    // Session expirée ou absente : retour à la page de garde (login serveur).
    // Lot « Le retour et l'adresse » : l'adresse courante est gardée, l'App la reprend après la connexion.
    try { if(location.hash) sessionStorage.setItem("rr_adresse", location.hash); } catch(e2){ /* stockage indisponible */ }
    window.location.href = "/";
    throw new Error("unauthenticated");
  }
  if(!res.ok){
    let detail = "";
    try { const j = await res.json(); detail = j && j.detail; } catch(e){ /* pas de corps JSON */ }
    // Lot « La série juste » (v1.0104) : `err.detail` = le `detail` du corps tel quel (un objet pour un 409 du
    // Planning) ; `err.message` = ce `detail` quand c'est une chaîne, sinon `HTTP <statut>`.
    const err = new Error(typeof detail === "string" && detail ? detail : `HTTP ${res.status}`);
    err.status = res.status;
    err.detail = detail;
    throw err;
  }
  // Lot « La config d'escadre recopiée juste après un enregistrement » (v1.0092) : une écriture réussie de
  // l'Escadre ou d'une escadrille au Centre recopie aussitôt la config d'escadre, sans attente ; la réponse
  // rendue plus bas ne change pas.
  if(String((opts && opts.method) || "GET").toUpperCase() !== "GET"
     && (path.startsWith("/api/command/squadrons") || path.startsWith("/api/command/wing"))){
    syncWingConfigSuite();
  }
  if(res.status === 204) return null;
  return res.json();
}

/* ---------- Callsign (v0.35 §4) : retrait des préfixes CONNUS (wing +
   escadrilles .env) des noms affichés. Matcher partagé avec le back
   (app/config.py + app/events.py) : même échappement, même semantique. */
let NAME_PREFIXES = [];
let PREFIX_RE = null;

function escTok(t){
  return t.replace(/[.^$*+?{}()|[\]\\-]/g,"\\$&").replace(/\s+/g,"\\s*");
}

function callsign(name){
  if(!name || !PREFIX_RE) return name || "";
  let out = name, prev;
  do { prev = out; out = out.replace(PREFIX_RE, ""); } while(out !== prev && out);
  return out.trim() || name;
}

async function loadMe(){
  ME = await apiFetch("/api/me");
  NAME_PREFIXES = ME.name_prefixes || [];
  PREFIX_RE = NAME_PREFIXES.length ? new RegExp(
    "^\\s*\\[?\\s*(?:" + NAME_PREFIXES.map(escTok).join("|") + ")\\s*\\]?\\s*\\|?\\s*", "i"
  ) : null;
  ccSyncAdmin();
}
// Lot « La page Configuration du Centre » : l'onglet et la ligne de « Plus » (`data-cc-admin`) ne se montrent qu'à un
// administrateur ; rejoué chaque fois que ME est (re)chargé.
function ccSyncAdmin(){
  const admin = !!(ME && ME.is_admin === true);
  $$("[data-cc-admin]").forEach(el=>{ el.hidden = !admin; });
}

/* ---------- Compte / thème / langue ---------- */
// Lot « L'accès invité » (R10) : le bandeau `.guest-strip` (sous la barre du haut et sur l'accueil,
// au-dessus de la pastille « Connecté »). Caché pour un membre ; pour l'invité, le texte `invite_bandeau`
// avec `{date}` = l'échéance en date longue de la langue. Posé par `setLang`, donc à chaque changement de langue.
function renderGuestStrip(){
  const inv = ME && ME.invite;
  $$(".guest-strip").forEach(el=>{
    el.classList.toggle("hidden", !inv);
    if(inv){
      const date = new Date(inv.jusqua).toLocaleDateString(
        currentLang==="fr" ? "fr-FR" : "en-US", {day:"numeric", month:"long", year:"numeric"});
      el.textContent = t("invite_bandeau").split("{date}").join(date);
    }
  });
}

function renderAccountChip(){
  $("#connected-name").textContent = ME.name || "";
  $("#account-name").textContent = ME.name || "";
  // Lot « Manuel : le bouton ? » : le nom au survol à tous les paliers (le palier large n'affiche que la pastille).
  $("#account-chip").title = ME.name || "";
  $("#account-avatar").innerHTML = avatarHtml(ME.id, ME.avatar_hash, ME.name);
}

/* Lot « Manuel : le bouton ? » : l'écran que le lecteur a sous les yeux, pour ouvrir le Manuel Pilote à sa section.
   L'App ne connaît pas les numéros du manuel : elle donne l'id de l'écran (clé de manuel/contenu/vues.json), le
   manuel le traduit en ancre. 1) la première fenêtre ouverte parmi Rapport, Déposer, fiche d'évènement ; 2) sinon la
   vue la plus profonde de #screen-app (dernier `view-*` qui a une boîte, dans l'ordre du document) ; 3) sinon "". */
function currentScreenId(){
  for(const id of ["modal-report", "modal-deposer", "modal-overlay"]){
    const m = document.getElementById(id);
    if(m && !m.classList.contains("hidden")) return id;
  }
  const app = document.getElementById("screen-app");
  let found = "";
  if(app){
    app.querySelectorAll('[id^="view-"]').forEach(el=>{
      if(el.getClientRects().length > 0) found = el.id;
    });
  }
  return found;
}

/* Ouvre le manuel dans un onglet neuf à chaque appui (`"_blank"`), à la section de l'écran affiché.
   Lot « Manuel : le ? ouvre un onglet neuf » : plus d'onglet nommé -- Chrome Android garde quelques secondes
   l'onglet qu'on vient de fermer, et le nom le visait encore : l'appui ne montrait rien. */
function openManuel(){
  const id = currentScreenId();
  const w = window.open("/manuel/" + (id ? "#vue=" + id : ""), "_blank");
  if(w && w.focus) w.focus();
}

/* Thème GLOBAL (Lot 5 §1, révisé Lot 7) : `data-theme` posé sur
   `document.documentElement` pour que TOUT le document suive le thème
   actif, y compris les éléments injectés au `body` hors de `#screen-app`
   (toast, popovers, menus) — ce que l'ancien scope `.theme-scope` (Lot 4
   §6) ne couvrait pas. La landing (#screen-landing) suit désormais elle
   aussi le thème (Lot 7 §5quater) au lieu d'être verrouillée sombre.

   Modèle de préférence (Lot 7 §2) : `themePref` ∈ {"dark","light","system"},
   persistée dans localStorage["theme_pref_v1"]. Défaut (non défini) =
   "system". Le thème EFFECTIF se résout via resolveTheme(). `applyTheme()`
   est la fonction unique qui calcule l'effectif, pose `data-theme` +
   `currentTheme`, et met à jour TOUTES les instances du contrôle 3 états
   (app + landing) via le sélecteur commun `[data-theme-pref]` — pas de
   logique dupliquée entre les deux emplacements. */
let themePref = "system";

function resolveTheme(pref){
  if(pref === "system"){
    return window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
  }
  return pref;
}

function applyTheme(){
  const effective = resolveTheme(themePref);
  currentTheme = effective;
  document.documentElement.setAttribute("data-theme", effective);
  $$("[data-theme-pref]").forEach(btn=>{
    btn.classList.toggle("active", btn.dataset.themePref === themePref);
  });
}

function setThemePref(pref){
  themePref = pref;
  try { localStorage.setItem("theme_pref_v1", pref); } catch(e){ /* stockage indisponible : dégrade en silence */ }
  applyTheme();
}

function initialThemePref(){
  const stored = (function(){ try { return localStorage.getItem("theme_pref_v1"); } catch(e){ return null; } })();
  return (stored === "dark" || stored === "light" || stored === "system") ? stored : "system";
}

// Suivi du thème système (Lot 7 §3) : si la préférence courante est
// "system", tout changement de prefers-color-scheme au niveau OS doit
// rebasculer l'app en direct, sans rechargement.
window.matchMedia("(prefers-color-scheme: dark)").addEventListener("change", () => {
  if(themePref === "system") applyTheme();
});

/* Layout GLOBAL (Lot 0 socle, v0.40) : `data-layout` posé sur
   `document.documentElement`, 3 paliers, source de vérité UNIQUE pour la
   bascule de toutes les vues (remplace les 5 @media contradictoires —
   cf. GUIDE_DE_STYLE_READY_ROOM_v2 §7). Le script inline anti-FOUC du
   <head> d'index.html pose déjà `data-layout` avant le premier paint avec
   la même logique de seuils (dupliquée, volontairement autonome) ;
   applyLayout() ici reprend la main pour les changements en cours de
   session (resize, rotation d'écran). Purement CSS : aucun re-render
   applicatif n'est requis quand le palier change. */
function resolveLayout(){
  const w = window.innerWidth;
  const portrait = window.matchMedia("(orientation:portrait)").matches;
  if(w < 720) return "compact";
  // Lot « La Planification en grand écran » (v1.0077) : le palier wide commence à 1 600 px (il commençait à 1 440).
  if(w >= 1600) return "wide";
  if(w >= 1080 && !(portrait && w <= 1024)) return "large";
  return "intermediate";
}
function applyLayout(){
  document.documentElement.setAttribute("data-layout", resolveLayout());
  syncTopbarNavScroll();
}

// Lot M3 §C : l'intitule de colonne est porte par la cellule, pour le repli
// en blocs au palier compact. Une seule ecriture pour les CINQ tableaux du
// Commandement, et pour ceux a venir. Appelee APRES chaque remplissage de
// tbody -- jamais une fois au demarrage, les cinq ne se remplissent pas au
// meme moment. La ligne de groupe (une seule cellule en colspan) recoit
// l'intitule de la premiere colonne : le CSS l'eteint (tr.cc-group td::before).
function ccStampLabels(scope){
  const racine = scope || document;
  racine.querySelectorAll('#screen-app[data-module="command"] table.cc-table').forEach(tb=>{
    const ths = Array.from(tb.querySelectorAll("thead th"), h => h.textContent.trim());
    tb.querySelectorAll("tbody tr").forEach(tr=>{
      Array.from(tr.children).forEach((td,i)=>{ if(ths[i]) td.setAttribute("data-label", ths[i]); });
    });
  });
}

// Lot A, geste 1 (v0.9920) : la nav défile aux paliers intermediate/large.
// Lot M3 §A10 (v0.9936) : le palier compact défile désormais aussi (tab bar
// basse scrollable) -- la garde qui l'excluait a été retirée, la fonction
// s'applique uniformément à tous les paliers. Deux garde-fous, rien de plus :
// (1) `.fits` éteint le fondu de bord quand tout tient déjà (scrollWidth
// <= clientWidth + 2, ex. Planification à 2 entrées) ; (2) défilement
// jusqu'à l'entrée active. Trois `.topbar-nav` coexistent dans le DOM
// (planif/debrief/command, un seul visible à la fois via `hidden`) : on les
// traite toutes, sans effet sur celles masquées.
function syncTopbarNavScroll(){
  $$(".topbar-nav").forEach(nav=>{
    nav.classList.toggle("fits", nav.scrollWidth <= nav.clientWidth + 2);
    const active = nav.querySelector("button.active");
    if(active) active.scrollIntoView({block:"nearest", inline:"nearest"});
  });
}

let _layoutResizeTimer = null;
function scheduleApplyLayout(){
  clearTimeout(_layoutResizeTimer);
  _layoutResizeTimer = setTimeout(applyLayout, 120);
}
window.addEventListener("resize", scheduleApplyLayout);
// La rotation d'écran ne déclenche pas toujours "resize" de façon fiable
// selon les navigateurs mobiles -> écouteur matchMedia dédié en complément.
// v0.9916 (Lot C, geste ③) : au moment où l'event `change` part,
// `window.innerWidth` n'est pas encore à jour sur certains navigateurs
// mobiles -- resolveLayout() lu immédiatement resterait sur le palier
// d'avant rotation. On repousse d'une frame pour laisser le viewport se
// stabiliser avant de ré-résoudre. `resolveLayout()`/`scheduleApplyLayout()`
// restent inchangés -- le défaut est de moment, pas de seuil.
window.matchMedia("(orientation:portrait)").addEventListener("change", () => {
  requestAnimationFrame(applyLayout);
});

function initialLang(){
  const stored = (function(){ try { return localStorage.getItem("rr_lang_v1"); } catch(e){ return null; } })();
  if(stored === "fr" || stored === "en") return stored;
  return (ME && ME.lang === "en") ? "en" : "fr";
}

function setLang(lang){
  currentLang = lang;
  try { localStorage.setItem("rr_lang_v1", lang); } catch(e){ /* stockage indisponible : dégrade en silence */ }
  document.documentElement.lang = lang;
  $$(".lang-toggle button").forEach(b=> b.classList.toggle("active", b.dataset.lang===lang));
  $$("[data-i18n]").forEach(el=>{ el.textContent = t(el.dataset.i18n); });
  // Correctif v0.9909 : `data-i18n` reste `textContent` -- volontairement,
  // pour les 378 libellés existants (le balisage y serait rendu comme du
  // texte littéral, mais aucun n'en porte). `data-i18n-html` est
  // l'exception EXPLICITE et RÉSERVÉE aux deux paragraphes du dictionnaire
  // qui portent réellement du `<b>` (cc_rights_plan_hint,
  // cc_rights_ref_limit_hint) : injectée en innerHTML, donc jamais à
  // employer sur une valeur qu'un utilisateur pourrait saisir -- seulement
  // sur des littéraux du dictionnaire i18n, cf. brief Correctif v0.9909 §3①.
  $$("[data-i18n-html]").forEach(el=>{ el.innerHTML = t(el.dataset.i18nHtml); });
  $$("[data-i18n-ph]").forEach(el=>{ el.setAttribute("placeholder", t(el.dataset.i18nPh)); });
  // Lot « Le Centre de Commandement dit ce qu'il fait » (R11.3, R11.5) : même patron pour
  // l'`aria-label` et l'info-bulle des éléments du Centre qui les portent.
  $$("[data-i18n-aria]").forEach(el=>{ el.setAttribute("aria-label", t(el.dataset.i18nAria)); });
  $$("[data-i18n-title]").forEach(el=>{ el.setAttribute("title", t(el.dataset.i18nTitle)); });
  $("#back-to-landing").setAttribute("aria-label", t("back"));
  $("#back-to-landing").setAttribute("title", t("back"));
  renderGuestStrip();
  renderInvitesChamp();
  renderAll();
  afficherCompteur();   // Lot v1.0074 : le compteur se retraduit sans relire (aucune requête)
  // Lot D2③ : contenu dynamique (rendu depuis l'état, pas via data-i18n) --
  // re-rendu si déjà chargé/ouvert. Les cartes de confirmation déjà
  // affichées dans la modale ne sont pas rétro-traduites (contenu figé
  // d'un dépôt passé, cas limite non couvert).
  if(DEBRIEF_SESSIONS) renderMissions();
  if(!$("#modal-deposer").classList.contains("hidden")) renderDeposerFileList();
  if(!$("#modal-report").classList.contains("hidden")) renderModalReport();
  if(CURRENT_SESSION && sessionDetailLoadState === "ready") renderSession();
  if(CURRENT_FLIGHT  && flightDetailLoadState  === "ready") renderFlight();
  if(dossierLoadState === "ready") renderPilotes(); // Lot « L'écran A »
  // Lot « L'écran C » : le registre et la fiche, s'ils ont été demandés.
  if(campagnesLoadState !== "idle") renderCampagnes();
  if(CURRENT_CAMPAIGN_ID && campagneLoadState[CURRENT_CAMPAIGN_ID]) renderCampagne();
  if(commandEscadreLoadState === "ready" || commandEscadreLoadState === "error") renderCommandEscadre(); // lot « L'écran Escadre du Centre »
  if(commandRefLoadState === "ready" || commandRefLoadState === "error") renderCommandRef(); // lot « Les référentiels »
  if(commandArchLoadState === "ready" || commandArchLoadState === "error") renderCommandArchives(); // lot « L'écran Archives du Centre »
  if(commandCfgLoadState === "ready" || commandCfgLoadState === "error") renderCommandConfig(); // lot « La page Configuration du Centre »
}

/* ---------- Temps réel (SSE) ---------- */
// Lot « rr-socle-proprete » (v1.0111) : le flux coupé se dit, ou se rouvre seul.
let fluxPerdu = false;     // le message de session expirée ne se dit qu'une fois par chargement de la page
let fluxRouvert = false;   // le flux vient d'être rouvert par nous : à sa première ouverture, les évènements se rechargent
let fluxAttente = null;    // le délai en cours avant la relecture de `/api/me`
const FLUX_ATTENTE_MS = 5000;

function connectSSE(){
  if(eventSource) eventSource.close();
  eventSource = new EventSource("/api/stream");
  eventSource.onopen = ()=>{
    if(!fluxRouvert) return;
    fluxRouvert = false;
    // L'écran rattrape ce qu'il a manqué pendant la coupure.
    pendingRefetch.events = true;
    scheduleRefetch();
  };
  eventSource.onmessage = (ev)=>{
    let msg;
    try { msg = JSON.parse(ev.data); } catch(e){ return; }
    if(!msg || msg.type !== "invalidate") return;
    if(msg.scope === "events"){
      pendingRefetch.events = true;
    } else if(msg.scope === "presences"){
      pendingRefetch.presences = true;
      pendingRefetch.lastEventId = msg.event_id;
      pendingRefetch.lastOccDate = msg.occ_date;
    } else if(msg.scope === "report"){
      // Lot R6 §5① -- le canal n'a aucune mémoire, il ne fait que réveiller
      // ceux déjà là. `event_id` porte ici un id de SESSION (impropre au
      // nom du champ, cf. app/debrief/api.py) : `publish_invalidate` est
      // partagée avec huit sites du calendrier, sa signature ne bouge pas.
      pendingRefetch.report = true;
      pendingRefetch.lastReportSessionId = msg.event_id;
    }
    scheduleRefetch();
  };
  // Une coupure passagère : le navigateur se reconnecte seul (readyState CONNECTING), rien à faire.
  // Flux fermé (une réponse refusée : 401, 502…) : le navigateur n'essaie plus.
  eventSource.onerror = ()=>{
    if(eventSource.readyState !== EventSource.CLOSED) return;
    attendreFlux();
  };
}

// Flux fermé : 5 s, puis `/api/me` par `fetch` direct (pas `apiFetch`, qui renverrait à la page de connexion).
// 401 : la session a expiré, un message, plus aucune tentative ; 200 : le flux se rouvre ;
// toute autre réponse ou une erreur réseau : 5 s de plus, puis on relit.
function attendreFlux(){
  if(fluxAttente || fluxPerdu) return;
  fluxAttente = setTimeout(async ()=>{
    fluxAttente = null;
    let statut = 0;
    try {
      const res = await fetch("/api/me", {credentials:"same-origin"});
      statut = res.status;
    } catch(e){ /* réseau injoignable : on relira */ }
    if(statut === 401){
      fluxPerdu = true;
      showToast(t("error_stream_lost"), "erreur");
      return;
    }
    if(statut === 200){
      fluxRouvert = true;
      connectSSE();
      return;
    }
    attendreFlux();
  }, FLUX_ATTENTE_MS);
}

function scheduleRefetch(){
  if(refetchTimer) clearTimeout(refetchTimer);
  refetchTimer = setTimeout(flushRefetch, DEBOUNCE_MS);
}

/* scope="events"    -> re-fetch la vue calendrier courante (+ hebdo si affiché).
   scope="presences" -> re-fetch les compteurs (vue courante) + le détail ouvert
   concerné si son (event_id, occ_date) correspond. Toujours par ré-écriture
   complète depuis la vérité serveur (jamais d'incrément local) : le re-fetch
   est donc intrinsèquement idempotent vis-à-vis de la mise à jour optimiste
   du RSVP (cf. vigilance brief). */
async function flushRefetch(){
  refetchTimer = null;
  const doEvents = pendingRefetch.events;
  const doPresences = pendingRefetch.presences;
  const targetEventId = pendingRefetch.lastEventId;
  const targetOccDate = pendingRefetch.lastOccDate;
  const doReport = pendingRefetch.report;
  const targetReportSessionId = pendingRefetch.lastReportSessionId;
  pendingRefetch = { events:false, presences:false, lastEventId:null, lastOccDate:null, report:false, lastReportSessionId:null };

  const appVisible = !$("#screen-app").classList.contains("hidden");
  if(appVisible && (doEvents || doPresences)){
    await refreshCurrentCalendarView();
    // Lot 4 §4 : le hebdo doit se rafraîchir en direct dès lors qu'il est
    // la vue active — plus seulement "pas caché" (même condition en
    // pratique, mais exprimée sur l'état applicatif, plus robuste) — et
    // rester marqué "stale" sinon, pour forcer un refetch au prochain
    // passage sur l'onglet (cf. switchAppView) plutôt que de réafficher
    // un tableau périmé depuis le cache.
    if(currentAppView === "hebdo"){
      await refreshHebdo();
    } else {
      hebdoStale = true;
    }
  }
  if(doPresences && currentModalMode === "view" && currentModalEventId
     && currentModalEventId === targetEventId && currentModalOccDate === targetOccDate){
    await refreshOpenDetail();
  }
  // Lot R6 §5① -- le canal parle à tous, chaque client ignore ce qui ne le
  // concerne pas : re-fetch seulement si la modale Rapport est ouverte ET
  // que l'invalidation porte sur la session actuellement affichée.
  if(doReport && !$("#modal-report").classList.contains("hidden")
     && CURRENT_SESSION && CURRENT_SESSION.id === targetReportSessionId){
    await fetchReportData(CURRENT_SESSION.id);
  }
}

/* ---------- La Planche : fenêtre calendrier ---------- */
function monthGridRange(year, month){
  const firstOfMonth = new Date(year, month, 1);
  const startOffset = (firstOfMonth.getDay()+6)%7;
  const gridStart = new Date(year, month, 1 - startOffset);
  const daysInMonth = new Date(year, month+1, 0).getDate();
  let totalCells = startOffset + daysInMonth;
  totalCells = Math.ceil(totalCells/7)*7;
  const gridEnd = new Date(gridStart);
  gridEnd.setDate(gridStart.getDate() + totalCells - 1);
  return {gridStart, gridEnd};
}

/* Semaine (Lun-Dim) contenant `anchor` (Date JS). Lot 4 §2 : `anchor` est
   désormais navigable (`weekAnchor`), plus figé sur "aujourd'hui". */
function weekRangeForAnchor(anchor){
  const dow = (anchor.getDay()+6)%7;
  const monday = new Date(anchor); monday.setDate(anchor.getDate()-dow);
  const sunday = new Date(monday); sunday.setDate(monday.getDate()+6);
  return {gridStart:monday, gridEnd:sunday};
}

function indexOccurrences(occs){
  occurrencesByDate = new Map();
  (occs||[]).forEach(o=>{
    if(!occurrencesByDate.has(o.occ_date)) occurrencesByDate.set(o.occ_date, []);
    occurrencesByDate.get(o.occ_date).push(o);
  });
}

async function doFetchRange(from, to){
  const fromISO = toISODate(from), toISO_ = toISODate(to);
  let occs = [];
  try {
    occs = await apiFetch(`/api/events?from=${fromISO}&to=${toISO_}`);
  } catch(e){
    showToast(t("error_generic"), "erreur");
  }
  indexOccurrences(occs);
  renderAll();
  majCompteur();
}

// Lot « Ma réponse sur la Planche » (v1.0073) : « À répondre · N » dans la barre — les évènements des 14 prochains
// jours (aujourd'hui compris, tous types, filtres ignorés) sans réponse ; caché à 0 et pour un invité ; le clic
// ouvre la fiche du plus proche. Une erreur de lecture laisse le bouton tel quel.
// Lot « La Planche d'abord, la fiche qui répond » (v1.0074) : le dernier résultat appliqué est gardé ici
// (`{n, premiere}`, ou null pour « rien ») ; `afficherCompteur` rend le bouton de ce seul résultat, sans requête
// (c'est ce qui permet à `setLang` de le retraduire) ; un jeton de génération écarte une lecture devenue
// plus ancienne qu'une autre déjà lancée.
let compteurResultat = null;
let compteurJeton = 0;

function afficherCompteur(){
  const btn = $("#mr-compteur");
  if(!btn) return;
  if(!compteurResultat){ btn.classList.add("hidden"); btn.onclick = null; return; }
  const {n, premiere} = compteurResultat;
  btn.innerHTML = `${pip("todo")}<span>${t('to_answer')} · ${n}</span>`;
  btn.onclick = ()=> openEventModal(premiere.event_id, premiere.occ_date);
  btn.classList.remove("hidden");
}

async function majCompteur(){
  if(!$("#mr-compteur")) return;
  const jeton = ++compteurJeton;
  const du = new Date(), au = new Date();
  au.setDate(au.getDate()+13);
  let liste;
  try {
    liste = await apiFetch(`/api/events?from=${toISODate(du)}&to=${toISODate(au)}`);
  } catch(e){ return; }
  if(jeton !== compteurJeton) return;
  // Lot « La Planification en grand écran » (v1.0077) : la même lecture sert le panneau « À venir » — gardée au niveau
  // du module, aussi pour un invité (qui lisait déjà la Planche ; son compteur reste « rien » : `monEtat` ne lui rend rien).
  aVenirListe = liste || [];
  const aRepondre = (liste||[]).filter(o=> monEtat(o)==="todo")
    .sort((a,b)=> new Date(a.start_at_utc) - new Date(b.start_at_utc));
  compteurResultat = aRepondre.length ? {n:aRepondre.length, premiere:aRepondre[0]} : null;
  afficherCompteur();
  renderAVenir();
}

// Lot « La Planification en grand écran » (v1.0077) : le panneau « À venir » (`#pl-aside`, visible dès 1 600 px).
// `aVenirListe` : la lecture de `majCompteur` (14 jours glissants, aujourd'hui compris) ; `plSeul` : le filtre
// « À répondre » du panneau (faux au départ, remis à faux quand plus rien n'attend de réponse).
let aVenirListe = [];
let plSeul = false;

function renderAVenir(){
  const aside = $("#pl-aside");
  if(!aside) return;
  const loc = currentLang==="fr" ? "fr-FR" : "en-GB";
  const fmtJour = {weekday:"short", day:"numeric", month:"short"};
  const maintenant = new Date();
  // Les occurrences terminées (début + durée, 120 min par défaut) ne sont plus « à venir ».
  const restantes = aVenirListe.filter(o=>{
    const fin = new Date(o.start_at_utc).getTime() + (o.duration_min || 120)*60000;
    return fin > maintenant.getTime();
  }).sort((a,b)=> new Date(a.start_at_utc) - new Date(b.start_at_utc));
  const nbRepondre = restantes.filter(o=> monEtat(o)==="todo").length;
  if(nbRepondre === 0) plSeul = false;
  document.documentElement.toggleAttribute("data-pl-seul", plSeul);
  const montrees = plSeul ? restantes.filter(o=> monEtat(o)==="todo") : restantes;

  const fin = new Date(); fin.setDate(fin.getDate()+13);
  const sous = t("upcoming_until").replace("{date}", fin.toLocaleDateString(loc, fmtJour));
  const aujourdhui = toISODate(maintenant);

  let tete = `<div class="pl-aside-titre"><h3 id="pl-aside-titre">${t("agenda_upcoming")}</h3><span class="pl-aside-sous">${escapeHtml(sous)}</span></div>`;
  if(nbRepondre > 0 && !estInviteEcran()){
    tete += `<button type="button" class="pl-a-repondre" aria-pressed="${plSeul}">${pip("todo")}<span>${t("to_answer")} · <b>${nbRepondre}</b></span></button>`;
  }

  let corps;
  if(montrees.length === 0){
    corps = `<div class="pl-vide">${t(plSeul ? "upcoming_none_todo" : "upcoming_none")}</div>`;
  } else {
    const jours = [];
    montrees.forEach(o=>{
      let j = jours[jours.length-1];
      if(!j || j.date !== o.occ_date){ j = {date:o.occ_date, occs:[]}; jours.push(j); }
      j.occs.push(o);
    });
    corps = jours.map(j=>{
      const [y,m,d] = j.date.split("-").map(Number);
      const libelle = new Date(y, m-1, d).toLocaleDateString(loc, fmtJour).toUpperCase();
      const auj = j.date === aujourdhui ? ` <span class="pl-auj">${t("today_abbr")}</span>` : "";
      return `<div class="pl-jour"><div class="pl-jour-tete">${escapeHtml(libelle)}${auj}</div>${j.occs.map(carteAVenir).join("")}</div>`;
    }).join("");
  }

  const ancienne = aside.querySelector(".pl-liste");
  const defilement = ancienne ? ancienne.scrollTop : 0;
  aside.innerHTML = `<div class="pl-aside-head">${tete}</div><div class="pl-liste">${corps}</div>`;
  aside.querySelector(".pl-liste").scrollTop = defilement;
  marquerOuverte();
}

function carteAVenir(o){
  const etat = monEtat(o);
  const sel = (etat==="present" || etat==="maybe" || etat==="absent") ? etat : null;
  const texte = [typeLabel(o.type), o.game_label, o.map_name].filter(Boolean).join(" · ");
  const pc = o.presence_counts || {};
  let rsvp = "";
  if(!estInviteEcran()){
    const boutons = [["present","✓"],["maybe","~"],["absent","✗"]].map(([st,glyphe])=>
      `<button type="button" data-s="${st}"${sel===st ? ` class="sel-${st}"` : ""} aria-pressed="${sel===st}" title="${escapeAttr(t("rsvp_"+st))}">${glyphe}</button>`
    ).join("");
    rsvp = `<div class="pl-rsvp" role="group" aria-label="${escapeAttr(t("my_answer"))}">${boutons}</div>`;
  }
  return `<div class="pl-ev${o.type==="jeulibre" ? " jeulibre" : ""}${etat==="todo" ? " pl-todo" : ""}" data-k="${escapeAttr(occKey(o.event_id, o.occ_date))}" style="--chip-color:var(${TYPE_VAR[o.type]})" tabindex="0">`
    + `<div class="pl-ev-l1">${estInviteEcran() ? "" : maPastille(o)}<span class="pl-ev-heure">${fmtLocalTime(o.start_at_utc)}</span><span class="pl-ev-type">${TYPE_ICON[o.type]}${escapeHtml(texte)}</span>${newDot(o)}</div>`
    + `<div class="pl-ev-titre" title="${escapeAttr(o.title)}">${escapeHtml(o.title)}${o.recurring ? ` <span class="pl-rec">↻</span>` : ""}</div>`
    + `<div class="pl-ev-escadre"><span class="p">${pc.present||0} ✓</span> · <span class="m">${pc.maybe||0} ~</span> · <span class="a">${pc.absent||0} ✗</span></div>`
    + rsvp
    + `</div>`;
}

// Les gestes du panneau : un seul écouteur de clic, posé à l'initialisation.
function initPanneauAVenir(){
  const aside = $("#pl-aside");
  if(!aside) return;
  aside.addEventListener("click", async (e)=>{
    const bouton = e.target.closest(".pl-rsvp button");
    if(bouton && aside.contains(bouton)){
      e.stopPropagation();   // le clic ne remonte pas à la carte
      const carte = bouton.closest(".pl-ev");
      const [eventId, occDate] = carte.dataset.k.split("|");
      const etat = bouton.dataset.s;
      let ok = false;
      try {
        await apiFetch("/api/presences", {
          method:"PUT",
          headers:{"Content-Type":"application/json"},
          body: JSON.stringify({event_id:eventId, occ_date:occDate, state:etat})
        });
        ok = true;
      } catch(err){
        showToast(t("error_generic"), "erreur");
      }
      if(ok){
        showToast(t("rsvp_"+etat)+" ✓");
        await refreshCurrentCalendarView();   // la Planche, le compteur et le panneau se relisent
      }
      return;
    }
    if(e.target.closest(".pl-a-repondre")){
      plSeul = !plSeul;
      renderAVenir();
      return;
    }
    const carte = e.target.closest(".pl-ev");
    if(carte && aside.contains(carte)){
      const [eventId, occDate] = carte.dataset.k.split("|");
      openEventModal(eventId, occDate);
    }
  });
}

// L'évènement ouvert dans la fiche est cerclé, à la Planche comme au panneau (`pl-open`).
function marquerOuverte(){
  $$(".pl-open").forEach(el=> el.classList.remove("pl-open"));
  const ov = $("#modal-overlay");
  if(!ov || ov.classList.contains("hidden") || !currentModalEventId || !currentModalOccDate) return;
  const k = occKey(currentModalEventId, currentModalOccDate);
  $$("#cal-grid .cal-chip, #pl-aside .pl-ev").forEach(el=>{ if(el.dataset.k === k) el.classList.add("pl-open"); });
}

async function fetchAndRenderCalendar(){
  const {gridStart, gridEnd} = currentView === "month"
    ? monthGridRange(calYear, calMonth)
    : weekRangeForAnchor(weekAnchor);
  currentRangeFrom = gridStart; currentRangeTo = gridEnd;
  await doFetchRange(gridStart, gridEnd);
}

async function refreshCurrentCalendarView(){
  if(!currentRangeFrom || !currentRangeTo) return fetchAndRenderCalendar();
  await doFetchRange(currentRangeFrom, currentRangeTo);
}

function eventsForDate(dateStr){
  const list = occurrencesByDate.get(dateStr) || [];
  return list.filter(o=> activeFilters.has(o.type));
}

/* Helper partagé (Refonte Planning L2) : construit le bloc "jour" utilisé
   par l'agenda du mois ET par la vue Semaine (via renderWeekStrip). Un seul
   rendu DOM, reproduisant à l'identique l'ex-boucle inline de renderMonthGrid
   — la bascule visuelle (carte 7-colonnes ↔ liste) est 100% CSS via
   data-layout, aucun branchement JS par palier ici. */
function renderDayBlock(dateStr){
  const occs = eventsForDate(dateStr);
  const [y, mo, d] = dateStr.split("-").map(Number);
  const isToday = y===TODAY.y && (mo-1)===TODAY.m && d===TODAY.d;
  const jsDow = new Date(y, mo-1, d).getDay();
  const dow = WEEKDAYS[currentLang][(jsDow+6)%7];
  const dayEl = document.createElement("div");
  dayEl.className = "agenda-day" + (isToday?" is-today":"") + (occs.length?"":" empty");
  // Entête jour (prominent) — clic sur l'entête = synthèse du jour
  const head = document.createElement("div");
  head.className = "agenda-day-head";
  head.innerHTML = `<span class="ad-dow">${dow}</span><span class="ad-num">${d}</span>`
    + `<span class="ad-mon">${MONTHS[currentLang][mo-1].slice(0,3)}</span>`
    + (isToday?` <span class="ad-today">${t('today_abbr')}</span>`:"");
  head.addEventListener("click", ()=> openDayModal(dateStr));
  dayEl.appendChild(head);
  if(occs.length){
    const evs = document.createElement("div"); evs.className="agenda-day-events";
    occs.forEach(occ=>{
      const ev=document.createElement("div"); ev.className="agenda-ev"+(occ.type==="jeulibre"?" jeulibre":"")+(monEtat(occ)==="todo"?" mr-todo":"");
      ev.style.setProperty("--chip-color", `var(${TYPE_VAR[occ.type]})`);
      ev.innerHTML = `<div class="agenda-ev-title">${maPastille(occ)}<span class="ico">${TYPE_ICON[occ.type]}</span>`
        + `<span>${escapeHtml(occ.title)}</span>${occ.recurring?' <span style="opacity:.7">↻</span>':''}`
        + `${typeof newTag==="function"?newTag(occ):""}</div>`
        + `<div class="agenda-ev-meta"><span class="ev-time">${fmtLocalTime(occ.start_at_utc)}</span> · <b>${occ.presence_counts.present} ✓</b> · <i>${occ.presence_counts.maybe} ~</i></div>`;
      ev.addEventListener("click",(e)=>{ e.stopPropagation(); openEventModal(occ.event_id, occ.occ_date); });
      evs.appendChild(ev);
    });
    dayEl.appendChild(evs);
  } else {
    const dash = document.createElement("div"); dash.className="day-empty-dash"; dash.textContent="—";
    dayEl.appendChild(dash);
  }
  return dayEl;
}

/* ---------- Rendu : La Planche ---------- */
function renderMonthGrid(){
  const grid = $("#cal-grid");
  const agenda = $("#agenda-list");
  grid.innerHTML=""; agenda.innerHTML="";
  WEEKDAYS[currentLang].forEach(w=>{
    const d=document.createElement("div"); d.className="cal-weekday"; d.textContent=w; grid.appendChild(d);
  });
  updateCalLabel();

  const firstOfMonth = new Date(calYear, calMonth, 1);
  let startOffset = (firstOfMonth.getDay()+6)%7;
  const daysInMonth = new Date(calYear, calMonth+1, 0).getDate();
  const daysInPrevMonth = new Date(calYear, calMonth, 0).getDate();

  const cells = [];
  for(let i=startOffset-1;i>=0;i--) cells.push({d:daysInPrevMonth-i, outside:true});
  for(let d=1; d<=daysInMonth; d++) cells.push({d, outside:false});
  let nextDay = 1;
  while(cells.length % 7 !== 0) cells.push({d: nextDay++, outside:true});

  cells.forEach((cell, cellIndex)=>{
    const cellDiv = document.createElement("div");
    cellDiv.className = "cal-day" + (cell.outside?" outside":"");
    const dateStr = !cell.outside ? `${calYear}-${pad2(calMonth+1)}-${pad2(cell.d)}` : null;
    const isToday = !cell.outside && calYear===TODAY.y && calMonth===TODAY.m && cell.d===TODAY.d;
    if(isToday) cellDiv.classList.add("today");

    const dow = WEEKDAYS[currentLang][cellIndex % 7];
    const num = document.createElement("div"); num.className="cal-daynum";
    const numLabel = isToday ? `<span class="cal-num-today">${cell.d}</span>` : cell.d;
    num.innerHTML = `<span class="cal-dow">${dow}</span>` + numLabel;
    cellDiv.appendChild(num);

    const chipsWrap = document.createElement("div"); chipsWrap.className="cal-chips";
    if(dateStr){
      const occs = eventsForDate(dateStr);
      const CAL_CHIP_CAP = 3;
      occs.slice(0, CAL_CHIP_CAP).forEach(occ=>{
        const chip=document.createElement("div"); chip.className="cal-chip"+(occ.type==="jeulibre"?" jeulibre":"")+(monEtat(occ)==="todo"?" mr-todo":"");
        chip.dataset.k = occKey(occ.event_id, occ.occ_date);   // Lot « La Planification en grand écran » (v1.0077) : repère de l'évènement ouvert (marquerOuverte)
        chip.style.setProperty("--chip-color", `var(${TYPE_VAR[occ.type]})`);
        // Lot « Ma réponse sur la Planche » : ma pastille, l'heure locale, le titre, le point NOUVEAU ; plus d'icône de type au mois.
        chip.innerHTML = `${maPastille(occ)}<span class="mr-time">${fmtLocalTime(occ.start_at_utc)}</span><span class="mr-titre">${escapeHtml(occ.title)}</span>${newDot(occ)}` + (occ.recurring? `<span class="rec" title="${t('recurring')}">↻</span>`:"");
        // stopPropagation : un clic sur un chip ouvre le DÉTAIL de l'occurrence,
        // pas la création (Lot 4 §3 — ne jamais déclencher les deux à la fois).
        chip.addEventListener("click", (e)=>{ e.stopPropagation(); openEventModal(occ.event_id, occ.occ_date); });
        chipsWrap.appendChild(chip);
      });
      if(occs.length > CAL_CHIP_CAP){
        // Pas de stopPropagation ici : un clic sur "+N" doit laisser la case
        // ouvrir la synthèse du jour, comme le reste de la case (Lot V §A2).
        const more = document.createElement("div"); more.className="cal-more";
        more.textContent = `+${occs.length - CAL_CHIP_CAP}`;
        chipsWrap.appendChild(more);
      }
      if(occs.length){
        const totalPresent = occs.reduce((a,o)=>a+o.presence_counts.present,0);
        const totalMaybe = occs.reduce((a,o)=>a+o.presence_counts.maybe,0);
        const totalAbsent = occs.reduce((a,o)=>a+o.presence_counts.absent,0);
        if(totalPresent+totalMaybe+totalAbsent > 0){
          const gauge = document.createElement("div"); gauge.className="cal-presence";
          // Lot « Les finitions de l'édition » (v1.0103, ARU-23) : les absents au compteur du jour, sans `title`.
          gauge.innerHTML = `<span class="cp-present">${totalPresent} ✓</span> · <span class="cp-maybe">${totalMaybe} ~</span> · <span class="cp-absent">${totalAbsent} ✗</span>`;
          chipsWrap.appendChild(gauge);
        }
      }
    }
    cellDiv.appendChild(chipsWrap);
    // Lot C : clic sur une case-date (tout jour du mois affiché, avec ou
    // sans droit de création) -> modale SYNTHÈSE DU JOUR (liste des events +
    // inscrits). La création directe est relocalisée dans cette modale
    // ("+ Créer ce jour", gated event.create) — remplace l'ancien clic ->
    // création directe (Lot 4 §3), jugé perturbant.
    if(dateStr){
      cellDiv.classList.add("cal-day-clickable");
      cellDiv.addEventListener("click", ()=> openDayModal(dateStr));
    }
    grid.appendChild(cellDiv);
  });

  // Agenda mobile (Lot v0.37, refonte portée Lot 1) : liste JOUR PAR JOUR.
  // Volet C : bascule "À venir" (défaut, masque passé + jours vides) /
  // "Tout le mois" (comportement historique, jours vides inclus).
  const scopeToggle = document.createElement("div"); scopeToggle.className="agenda-scope-toggle";
  const todayISO = `${TODAY.y}-${pad2(TODAY.m+1)}-${pad2(TODAY.d)}`;
  [["upcoming","agenda_upcoming"],["all","agenda_all"]].forEach(([scope,key])=>{
    const btn = document.createElement("button");
    btn.type = "button";
    btn.className = agendaScope===scope ? "active" : "";
    btn.textContent = t(key);
    btn.addEventListener("click", ()=>{
      if(agendaScope===scope) return;
      agendaScope = scope;
      localStorage.setItem("agenda_scope_v1", agendaScope);
      renderMonthGrid();
    });
    scopeToggle.appendChild(btn);
  });
  agenda.appendChild(scopeToggle);

  let anyDayRendered = false;
  for(let d=1; d<=daysInMonth; d++){
    const dateStr = `${calYear}-${pad2(calMonth+1)}-${pad2(d)}`;
    const occs = eventsForDate(dateStr);
    if(agendaScope==="upcoming" && (dateStr < todayISO || occs.length===0)) continue;
    anyDayRendered = true;
    agenda.appendChild(renderDayBlock(dateStr));
  }
  if(agendaScope==="upcoming" && !anyDayRendered){
    const empty = document.createElement("div"); empty.className="agenda-empty";
    empty.textContent = t("agenda_empty_upcoming");
    agenda.appendChild(empty);
  }
}

/* Libellé de la barre de nav + aria/title des boutons ‹ › — dépend de la
   vue active (Lot 4 §2 : nav contextuelle à `currentView`). */
function updateCalLabel(){
  if(currentView === "month"){
    $("#month-label").textContent = MONTHS[currentLang][calMonth] + " " + calYear;
    $("#month-prev").setAttribute("aria-label", t("month_prev"));
    $("#month-prev").setAttribute("title", t("month_prev"));
    $("#month-next").setAttribute("aria-label", t("month_next"));
    $("#month-next").setAttribute("title", t("month_next"));
  } else {
    const {gridStart:monday, gridEnd:sunday} = weekRangeForAnchor(weekAnchor);
    $("#month-label").textContent = fmtWeekRange(monday, sunday);
    $("#month-prev").setAttribute("aria-label", t("week_prev"));
    $("#month-prev").setAttribute("title", t("week_prev"));
    $("#month-next").setAttribute("aria-label", t("week_next"));
    $("#month-next").setAttribute("title", t("week_next"));
  }
}

function renderWeekStrip(){
  const strip = $("#week-strip"); strip.innerHTML="";
  const {gridStart:monday} = weekRangeForAnchor(weekAnchor);
  for(let i=0;i<7;i++){
    const d = new Date(monday); d.setDate(monday.getDate()+i);
    const dateStr = toISODate(d);
    strip.appendChild(renderDayBlock(dateStr));
  }
}

function renderFilterChips(){
  const wrap = $("#filter-chips"); wrap.innerHTML="";
  // Lot « Correctif du grand écran » (v1.0078) : un jour (AAAA-MM-JJ) que la vue montre ?
  const prefixeMois = `${calYear}-${pad2(calMonth+1)}-`;
  const {gridStart:lundi, gridEnd:dimanche} = weekRangeForAnchor(weekAnchor);
  const debutSemaine = toISODate(lundi), finSemaine = toISODate(dimanche);
  const visibles = dateStr=> currentView === "month"
    ? dateStr.startsWith(prefixeMois)
    : (dateStr >= debutSemaine && dateStr <= finSemaine);
  ["entrainement","mission","campagne","jeulibre"].forEach(type=>{
    const chip=document.createElement("button"); chip.className="chip-filter"+(activeFilters.has(type)?" on":"");
    chip.style.setProperty("--chip-color", `var(${TYPE_VAR[type]})`);
    // Lot « La Planification en grand écran » (v1.0077) : l'état du filtre en `aria-pressed`, et le nombre d'occurrences
    // de ce type après le libellé (le compte suit la règle du v1.0078 ci-dessous).
    chip.setAttribute("aria-pressed", activeFilters.has(type) ? "true" : "false");
    // Lot « Correctif du grand écran » (v1.0078) : le nombre ne compte que les jours que la vue montre — en vue Mois, les
    // dates du mois affiché (la grille du lundi au dimanche charge aussi des jours des mois voisins, qu'elle ne montre pas) ;
    // en vue Semaine, les sept jours de la semaine de `weekAnchor` —, toujours par type et filtres ignorés.
    let nbType = 0;
    occurrencesByDate.forEach((liste, dateStr)=>{
      if(!visibles(dateStr)) return;
      liste.forEach(o=>{ if(o.type===type) nbType++; });
    });
    chip.innerHTML = `<span class="ico">${TYPE_ICON[type]}</span><span>${typeLabel(type)}</span><span class="pl-count">${nbType}</span>`;
    chip.addEventListener("click", ()=>{
      if(activeFilters.has(type)) activeFilters.delete(type); else activeFilters.add(type);
      renderFilterChips(); renderMonthGrid(); renderWeekStrip();
    });
    wrap.appendChild(chip);
  });
}

/* ---------- Tableau hebdo ---------- */
function fmtWeekRange(monday, sunday){
  const dd = n=> String(n).padStart(2,"0");
  if(monday.getMonth()===sunday.getMonth()){
    return `${dd(monday.getDate())}–${dd(sunday.getDate())} ${MONTHS[currentLang][sunday.getMonth()]} ${sunday.getFullYear()}`;
  }
  return `${dd(monday.getDate())} ${MONTHS[currentLang][monday.getMonth()]} – ${dd(sunday.getDate())} ${MONTHS[currentLang][sunday.getMonth()]} ${sunday.getFullYear()}`;
}

function indexProfiles(members){
  PROFILES = new Map((members||[]).map(m=> [String(m.id), m]));
}

async function refreshHebdo(){
  if(!hebdoAnchor) return null;
  try {
    hebdoData = await apiFetch(`/api/hebdo?anchor=${hebdoAnchor}`);
  } catch(e){
    showToast(t("error_generic"), "erreur");
    return null;
  }
  hebdoStale = false;
  indexProfiles(hebdoData.members);
  renderHebdo();
  return hebdoData;
}

function renderHebdo(){
  const container = $("#hebdo-sections"); container.innerHTML="";
  if(!hebdoData) return;
  renderHebdoSection(container, "hebdo_current", hebdoData.current_week);
  renderHebdoSection(container, "hebdo_next", hebdoData.next_week);
}

function renderHebdoSection(container, titleKey, week){
  const section = document.createElement("div"); section.className="hebdo-section";
  const title = document.createElement("div"); title.className="hebdo-section-title"; title.textContent = t(titleKey);
  const [sy,sm,sd] = week.start.split("-").map(Number);
  const [ey,em,ed] = week.end.split("-").map(Number);
  const monday = new Date(sy,sm-1,sd), sunday = new Date(ey,em-1,ed);
  const range = document.createElement("div"); range.className="hebdo-range";
  range.textContent = fmtWeekRange(monday, sunday);
  section.appendChild(title); section.appendChild(range);

  const evts = week.occurrences || [];
  if(evts.length > 0 && evts.length <= 2){
    section.classList.add("hebdo-fewevents");
  }
  if(evts.length===0){
    const empty=document.createElement("div"); empty.className="hebdo-section-empty";
    empty.textContent = t("hebdo_empty");
    section.appendChild(empty);
    container.appendChild(section);
    return;
  }

  // Correctif Lot 6 : ne lister que les membres ayant >=1 RSVP (present/
  // maybe/absent) sur >=1 occurrence de CETTE semaine. `PROFILES` (via
  // indexProfiles) reste alimenté par la liste COMPLETE hebdoData.members
  // -- ne jamais filtrer avant cet appel, creatorName() en depend.
  const registered = new Set();
  evts.forEach(occ => Object.keys(occ.states||{}).forEach(id => registered.add(String(id))));
  const shownMembers = (hebdoData.members||[]).filter(m => registered.has(String(m.id)));

  if(shownMembers.length===0){
    const empty=document.createElement("div"); empty.className="hebdo-section-empty";
    empty.textContent = t("hebdo_no_rsvp");
    section.appendChild(empty);
    container.appendChild(section);
    return;
  }

  const wrap = document.createElement("div"); wrap.className="hebdo-wrap";
  const table = document.createElement("table"); table.className="hebdo";
  const thead = document.createElement("thead");
  const theadRow = document.createElement("tr");
  theadRow.innerHTML = `<th class="col-member"></th>`;
  evts.forEach(occ=>{
    const [y,m,d]=occ.occ_date.split("-");
    const sub = [occ.game_label, occ.map_name].filter(Boolean).join(" · ");
    // Correctif R6.1 §A2 : occ.presence_counts est absent de /api/hebdo --
    // compteurs recalculés depuis occ.states (déjà présent, alimente les
    // cellules pip), sur les seuls shownMembers (membres affichés).
    const c={present:0,maybe:0,absent:0};
    shownMembers.forEach(m=>{ const s=(occ.states||{})[m.id]; if(s) c[s]++; });
    const th=document.createElement("th");
    th.innerHTML = `<div class="hebdo-col-head" style="--chip-color:var(${TYPE_VAR[occ.type]})">
        <span class="ico">${TYPE_ICON[occ.type]}</span>
        <span class="hebdo-col-name" title="${escapeAttr(occ.title)}">${escapeHtml(occ.title)}${occ.recurring?" ↻":""}${newTag(occ)}</span>
        ${sub ? `<span class="hebdo-col-sub" title="${escapeAttr(sub)}">${escapeHtml(sub)}</span>` : ""}
        <span class="d">${d}/${m} · ${fmtLocalTime(occ.start_at_utc)}</span>
        ${presenceGaugeHtml(c)}
      </div>`;
    theadRow.appendChild(th);
  });
  thead.appendChild(theadRow);

  // Lot v0.21 : groupement par escadrille -- ordre alphabetique, "Free
  // Agent" toujours en dernier quel que soit l'alphabet (le backend renvoie
  // deja "Free Agent" par defaut, cf. hebdo() / events.py).
  const groupsMap = new Map();
  shownMembers.forEach(m=>{
    const sq = m.squadron || "Free Agent";
    if(!groupsMap.has(sq)) groupsMap.set(sq, []);
    groupsMap.get(sq).push(m);
  });
  const groupKeys = Array.from(groupsMap.keys()).sort((a,b)=>{
    if(a==="Free Agent" && b==="Free Agent") return 0;
    if(a==="Free Agent") return 1;
    if(b==="Free Agent") return -1;
    return a.localeCompare(b);
  });
  groupKeys.forEach(sq=> groupsMap.get(sq).sort((a,b)=> a.name.localeCompare(b.name)));

  const colspan = 1 + evts.length;
  const tbody = document.createElement("tbody");
  groupKeys.forEach(sq=>{
    const trGroup = document.createElement("tr"); trGroup.className="hebdo-group";
    trGroup.innerHTML = `<td colspan="${colspan}"><span class="hebdo-group-label">${escapeHtml(sq)}</span></td>`;
    tbody.appendChild(trGroup);

    groupsMap.get(sq).forEach(member=>{
      const tr=document.createElement("tr");
      const tdName=document.createElement("td"); tdName.className="col-member";
      const isYou = ME && String(member.id)===String(ME.id);
      if(isYou) tr.classList.add("hebdo-you");
      // Label escadrille par pilote retire (Lot v0.21) : l'info est
      // desormais portee par la bande d'entete de groupe ci-dessus.
      tdName.innerHTML = escapeHtml(callsign(member.name));
      tr.appendChild(tdName);
      evts.forEach(occ=>{
        const td=document.createElement("td"); td.className="pip-cell";
        const state = (occ.states||{})[member.id];
        if(state) td.classList.add("state-"+state);
        if(!state){
          td.innerHTML = `<span style="opacity:.35">—</span>`;
        } else {
          const choice = (occ.choices||{})[member.id];
          const choiceLine = (state==="present"||state==="maybe") ? formatChoiceLine(choice) : "";
          td.innerHTML = `<span class="pip-${state}" title="${t('rsvp_'+state)}">${pip(state)}</span>`
            + (choiceLine ? `<div class="hebdo-cell-choice">${choiceLine}</div>` : "");
        }
        tr.appendChild(td);
      });
      tbody.appendChild(tr);
    });
  });
  table.appendChild(thead); table.appendChild(tbody);

  // Lot v0.21 : ligne de synthese agregee par occurrence (presents
  // uniquement), calculee cote front a partir de occ.choices.
  const tfoot = document.createElement("tfoot");
  const trTotals = document.createElement("tr"); trTotals.className="hebdo-totals";
  trTotals.innerHTML = `<td class="col-member">${escapeHtml(t("hebdo_totals"))}</td>`;
  evts.forEach(occ=>{
    const td=document.createElement("td"); td.className="hebdo-totals-cell";
    const tot = computeOccTotals(occ);
    td.innerHTML = (tot.aircraft || tot.missions)
      ? `${tot.aircraft?`<div class="synth-line"><span class="synth-lab">${t('hebdo_aircraft')}</span> ${tot.aircraft}</div>`:""}`
        +`${tot.missions?`<div class="synth-line"><span class="synth-lab">${t('hebdo_missions')}</span> ${tot.missions}</div>`:""}`
      : `<span style="opacity:.35">—</span>`;
    trTotals.appendChild(td);
  });
  tfoot.appendChild(trTotals);
  table.appendChild(tfoot);

  wrap.appendChild(table);

  // Lot v0.33 : bascule matrice -> cartes en portrait/tablette (memes
  // breakpoints que la bascule calendrier -> agenda, cf. guide §7). Les
  // DEUX rendus sont construits ; le CSS choisit lequel afficher.
  const cards = document.createElement("div"); cards.className="hebdo-cards";
  evts.forEach(occ=>{
    const buckets={present:[],maybe:[],absent:[]};
    shownMembers.forEach(m=>{
      const st=(occ.states||{})[m.id];
      if(st) buckets[st].push({m, choice:(occ.choices||{})[m.id]});
    });
    const [y,m,d]=occ.occ_date.split("-");
    const sub = [occ.game_label, occ.map_name].filter(Boolean).join(" · ");
    const metaStr = `${d}/${m} · ${fmtLocalTime(occ.start_at_utc)}` + (sub? ` · ${escapeHtml(sub)}` : "");

    const stateBlocks = ["present","maybe","absent"].map(st=>{
      const list = buckets[st];
      if(list.length===0) return "";
      const items = list.map(({m,choice})=>{
        const isYou = ME && String(m.id)===String(ME.id);
        const choiceLine = (st==="present"||st==="maybe") ? formatChoiceLine(choice) : "";
        const tagHtml = (m.squadron && m.squadron!=="Free Agent") ? ` <span class="hcm-tag">${escapeHtml(m.squadron)}</span>` : "";
        return `<li class="hebdo-card-member">
            <div class="hcm-name">${escapeHtml(callsign(m.name))}${tagHtml}</div>
            ${choiceLine?`<div class="hcm-choice">${choiceLine}</div>`:""}
          </li>`;
      }).join("");
      return `<div class="hebdo-card-state state-${st}">
          <div class="hebdo-card-state-label"><span class="pip-${st}">${pip(st)}</span> ${t('rsvp_'+st)} (${list.length})</div>
          <ul class="hebdo-card-members">${items}</ul>
        </div>`;
    }).join("");

    // Correctif R6.1 §A2 : compteurs carte dérivés des buckets déjà
    // calculés ci-dessus (present/maybe/absent, depuis occ.states).
    const cCard={present:buckets.present.length, maybe:buckets.maybe.length, absent:buckets.absent.length};
    const cardEl = document.createElement("div"); cardEl.className="hebdo-card";
    cardEl.style.setProperty("--chip-color", `var(${TYPE_VAR[occ.type]})`);
    cardEl.innerHTML = `
      <div class="hebdo-card-head">
        <span class="ico">${TYPE_ICON[occ.type]}</span>
        <span class="hebdo-card-title">${escapeHtml(occ.title)}${occ.recurring?" ↻":""}${newTag(occ)}</span>
        ${presenceGaugeHtml(cCard)}
      </div>
      <div class="hebdo-card-sub">${metaStr}</div>
      ${stateBlocks || `<div class="hebdo-card-empty">${t('hebdo_card_empty')}</div>`}
    `;
    cards.appendChild(cardEl);
  });

  section.appendChild(wrap);
  section.appendChild(cards);
  container.appendChild(section);
}

/* Lot v0.21 : formatte la ligne "appareil(s) · mission(s)" affichee sous le
   pip d'une cellule present/maybe. Robuste a choice absent (occ.choices ou
   l'entree du membre peuvent manquer -- cf. brief §2.2). */
function formatChoiceLine(choice){
  if(!choice) return "";
  const nw = s => `<span class="nw">${escapeHtml(s)}</span>`;
  const aircraftStr = (choice.aircraft||[]).map(nw).join(", ");
  const missions = choice.mission_types||[];
  let missionsStr = "";
  if(missions.length){
    const shown = missions.slice(0,2).map(c=>nw(missionLabel(c)));
    missionsStr = shown.join(", ");
    if(missions.length>2) missionsStr += ` +${missions.length-2}`;
  }
  if(aircraftStr && missionsStr) return `${aircraftStr} · ${missionsStr}`;
  return aircraftStr || missionsStr;
}

/* Lot v0.21 : decompte agrege (presents uniquement) par appareil et par
   mission pour une occurrence, tri decroissant par n puis code/libelle. */
function computeOccTotals(occ){
  const states = occ.states||{};
  const choices = occ.choices||{};
  const aircraftCounts = new Map();
  const missionCounts = new Map();
  Object.keys(states).forEach(pid=>{
    if(states[pid] !== "present") return;
    const choice = choices[pid];
    if(!choice) return;
    (choice.aircraft||[]).forEach(code=>{
      aircraftCounts.set(code, (aircraftCounts.get(code)||0)+1);
    });
    (choice.mission_types||[]).forEach(code=>{
      missionCounts.set(code, (missionCounts.get(code)||0)+1);
    });
  });
  const nw = s => `<span class="nw">${escapeHtml(s)}</span>`;
  const sortedParts = (map, labelFn) => Array.from(map.entries())
    .sort((a,b)=> b[1]-a[1] || String(labelFn(a[0])).localeCompare(String(labelFn(b[0]))))
    .map(([code,n])=> nw(`${labelFn(code)} ×${n}`)).join(" • ");
  return { aircraft: sortedParts(aircraftCounts, c=>c), missions: sortedParts(missionCounts, missionLabel) };
}

/* ---------- Modale : détail / RSVP ---------- */
function occKey(eventId, occDate){ return `${eventId}|${occDate}`; }

function showModalShell(fen){
  if(rrConfirmCourante) rrConfirmCourante(false);   // Lot « La charte commune de l'App » (v1.0079)
  $("#modal-overlay").classList.remove("hidden");
  rrFenetreOuverte(fen);   // Lot « Le retour et l'adresse » (v1.0101) : une fenêtre qui s'ouvre ajoute une entrée, une qui en remplace une autre la remplace
}

async function openEventModal(eventId, occDate, opts){
  currentModalEventId = eventId;
  currentModalOccDate = occDate;
  currentModalMode = "view";
  currentModalOccurrence = null;

  $("#modal-title").textContent = t("loading");
  $("#modal-desc").textContent = "";
  $("#modal-datetime").innerHTML = "";
  $("#modal-creator").textContent = "";
  $("#modal-presence-summary").innerHTML = ""; // Lot R3 §A2 : repeuplé par renderModalView()
  ficheSoireeNeuve();   // Lot « Les liens de la soirée » (v1.0107) : une fiche ouverte, une lecture
  $("#modal-accent-bar").style.setProperty("--modal-accent", "var(--accent)"); // Lot R3 §A1 : neutre le temps du fetch
  $("#rsvp-control").innerHTML = "";
  $("#roster-groups").innerHTML = "";
  // Lot 6 : reinitialisation des preferences RSVP a chaque ouverture --
  // sinon la selection de l'occurrence precedente resterait affichee un
  // instant avant le chargement de la nouvelle.
  prefsAircraft = [];
  prefsMissionTypes = [];
  currentYourState = null;
  rsvpPrefsVisible = false;
  $("#rsvp-prefs").classList.add("hidden");
  $("#aircraft-dropdown").classList.add("hidden");
  $("#recurrence-note").classList.add("hidden");
  $("#modal-edit-btn").classList.add("hidden");
  $("#modal-delete-btn").classList.add("hidden");
  $("#modal-save-btn").classList.add("hidden");
  $("#modal-rsvp-section").classList.remove("hidden");
  $("#modal-roster-section").classList.remove("hidden");
  showModalShell({t:"fiche", ev:eventId, date:occDate});
  marquerOuverte();   // Lot « La Planification en grand écran » (v1.0077) : l'évènement ouvert est cerclé

  let occ;
  try {
    occ = await apiFetch(`/api/events/${eventId}/occurrences/${occDate}`);
  } catch(e){
    // Lot « Le retour et l'adresse » : ouverte par l'adresse ou l'historique, une fiche qui répond 4xx (hors 401) dit « introuvable ».
    const introuvable = opts && opts.adresse && e && e.status >= 400 && e.status < 500 && e.status !== 401;
    showToast(t(introuvable ? "adresse_introuvable" : "error_generic"), "erreur");
    closeModal();
    return;
  }
  currentModalOccurrence = occ;
  renderModalView(occ);
}

async function refreshOpenDetail(){
  if(currentModalMode !== "view" || !currentModalEventId) return;
  let occ;
  try {
    occ = await apiFetch(`/api/events/${currentModalEventId}/occurrences/${currentModalOccDate}`);
  } catch(e){ return; }
  currentModalOccurrence = occ;
  renderModalView(occ);
}

function renderModalView(occ){
  $("#modal-accent-bar").style.setProperty("--modal-accent", `var(${TYPE_VAR[occ.type]})`); // Lot R3 §A1
  $("#modal-type-ico").innerHTML = TYPE_ICON[occ.type];
  $("#modal-type-ico").style.setProperty("--chip-color", `var(${TYPE_VAR[occ.type]})`);
  $("#modal-type-label").textContent = typeLabel(occ.type) + (occ.game_label? " · "+occ.game_label : "") + (occ.map_name? " · "+occ.map_name : "");
  $("#modal-type-label").style.color = `var(${TYPE_VAR[occ.type]})`;
  $("#modal-title").textContent = occ.title;

  const [y,m,d] = occ.occ_date.split("-");
  $("#modal-datetime").innerHTML = `
    <span>${d}/${m}/${y} · ${fmtLocalTime(occ.start_at_utc)}</span>
    ${occ.recurring? `<span class="badge-rec">↻ ${t('recurring')}</span>`:""}
  `;
  $("#modal-desc").textContent = occ.description || "";
  $("#modal-creator").textContent = t("creator")+" : "+creatorName(occ.created_by);

  $("#modal-rsvp-section").classList.remove("hidden");
  $("#modal-roster-section").classList.remove("hidden");
  $("#modal-save-btn").classList.add("hidden");

  const roster = occ.roster || {present:[], maybe:[], absent:[]};
  let yourState = null;
  ["present","maybe","absent"].forEach(st=>{
    (roster[st]||[]).forEach(p=>{ if(ME && String(p.profile_id)===String(ME.id)) yourState = st; });
  });
  currentYourState = yourState;
  // Lot R3 §A2 : pastille résumé de présence (N ✓ · N ~), sous la datetime.
  $("#modal-presence-summary").innerHTML = `<span class="modal-presence-pill"><span style="color:var(--rsvp-present)">${roster.present.length} ✓</span> · <span style="color:var(--rsvp-maybe)">${roster.maybe.length} ~</span></span>`;
  renderRsvpControl(yourState);
  renderRoster(roster);
  updatePrefsVisibility(true); // Lot R3 §A3 -- forcePopulate=true : ouverture, roster frais

  const canEdit = !!ME && (String(occ.created_by)===String(ME.id) || (ME.capabilities||[]).includes("event.edit_any"));
  $("#modal-edit-btn").classList.toggle("hidden", !canEdit);
  $("#modal-delete-btn").classList.toggle("hidden", !canEdit);
  // Lot « La Planche d'abord, la fiche qui répond » (v1.0074) : la portée de série ne sert qu'à Éditer et
  // Supprimer — visible pour une occurrence récurrente seulement quand `canEdit` montre ces deux boutons.
  $("#recurrence-note").classList.toggle("hidden", !(occ.recurring && canEdit));
  if(occ.recurring) $("#scope-select").value = "occurrence";
  updateRsvpSeriesVisibility();
  ficheSoireeRendre(occ);   // Lot « Les liens de la soirée » (v1.0107)
}

/* ---------- Lot « Les liens de la soirée » (v1.0107) : la fiche d'un évènement passé montre les sessions du même jour ----------
   Une lecture (`GET /api/debrief/soiree?jour=<occ_date>`) par fiche ouverte : `ficheSoiree` est remplacé à chaque
   ouverture et à chaque fermeture, et la réponse d'une lecture qui n'est plus celle de la fiche est ignorée. Un nouveau
   rendu de la même occurrence (présences invalidées) reprend le résultat sans relire. Un échec : rien, sans message. */
let ficheSoiree = {cle:null, etat:"rien", sessions:null};   // etat : rien | attente | ok | echec

function ficheSoireeCacher(){
  const el = $("#fiche-soiree");
  if(!el) return;
  el.classList.add("hidden");
  el.innerHTML = "";
}
function ficheSoireeNeuve(){
  ficheSoiree = {cle:null, etat:"rien", sessions:null};
  ficheSoireeCacher();
}
function ficheSoireeDessiner(sessions){
  const el = $("#fiche-soiree");
  const lignes = sessions.map(x=>{
    const meta = [
      x.duration_s != null ? fmtDuree(x.duration_s) : null,
      x.n_flights != null ? `${x.n_flights} ${t("meta_flights")}` : null,
    ].filter(m=> m).join(" · ");
    return `<a class="soiree-ligne" href="${escapeAttr(rrAdresseEcran("debrief", "session", {id: x.id}))}">`
      + `<span class="soiree-nom">${escapeHtml(x.display_title)}</span>`
      + `<span class="soiree-meta">${escapeHtml(meta)}</span>`
      + `<span class="soiree-chev" aria-hidden="true">›</span></a>`;
  });
  el.innerHTML = `<div class="modal-section-title">${escapeHtml(t("soiree_titre"))}</div>`
    + (lignes.length ? `<div class="soiree-liste">${lignes.join("")}</div>` : `<div class="soiree-vide">${escapeHtml(t("soiree_aucune"))}</div>`);
  el.classList.remove("hidden");
}
function ficheSoireeRendre(occ){
  const passee = new Date(occ.start_at_utc) < new Date();
  const droit = !!ME && (ME.capabilities||[]).includes("debrief.access");
  if(!passee || !droit){ ficheSoireeNeuve(); return; }   // à venir, ou sans l'accès à l'Escadre : rien n'est lu
  const cle = occKey(occ.event_id, occ.occ_date);
  if(ficheSoiree.cle === cle){
    if(ficheSoiree.etat === "ok") ficheSoireeDessiner(ficheSoiree.sessions);   // la même occurrence : le résultat déjà lu
    return;
  }
  // Une autre occurrence : un nouvel objet d'état, jamais l'ancien modifié en place (la réponse en retard de l'ancienne
  // se reconnaît à son objet et ne s'inscrit jamais comme résultat de la nouvelle).
  const f = {cle, etat:"attente", sessions:null};
  ficheSoiree = f;
  ficheSoireeCacher();
  apiFetch(`/api/debrief/soiree?jour=${encodeURIComponent(occ.occ_date)}`).then(rep=>{
    if(ficheSoiree !== f) return;   // une autre fiche, ou fermée : la réponse est ignorée
    f.sessions = (rep && rep.sessions) || [];
    f.etat = "ok";
    if(currentModalMode === "view" && occKey(currentModalEventId, currentModalOccDate) === cle) ficheSoireeDessiner(f.sessions);
  }, ()=>{
    if(ficheSoiree === f) f.etat = "echec";
  });
}

function renderRsvpControl(selectedState){
  const wrap = $("#rsvp-control");
  wrap.innerHTML = ["present","maybe","absent"].map(st=>`
    <button type="button" class="rsvp-opt${selectedState===st?' sel-'+st:''}" data-state="${st}">
      ${pip(st)}<span>${t('rsvp_'+st)}</span>
    </button>`).join("");
  $$(".rsvp-opt", wrap).forEach(btn=>{
    btn.addEventListener("click", async ()=>{
      const st = btn.dataset.state;
      currentYourState = st;
      renderRsvpControl(st); // optimiste : reflet immédiat dans le contrôle RSVP
      updatePrefsVisibility(); // Lot R3 §A3 : réévalue prefs visibles/masquées + peuple si nouvellement affichées
      await putPresence(st);
    });
  });
  updateRsvpSeriesVisibility();
}

/* v0.80 -- RSVP série : ligne secondaire visible seulement pour une
   occurrence récurrente ET après un choix RSVP (jamais un mode -- cf.
   brief §2.4). Appelée depuis renderRsvpControl() (fin) ET depuis
   renderModalView() (là où #recurrence-note est déjà géré), pour couvrir
   à la fois le clic RSVP et l'ouverture initiale de la modale. */
function updateRsvpSeriesVisibility(){
  const occ = currentModalOccurrence;
  const show = !!occ && !!occ.recurring && !!currentYourState;
  $("#rsvp-series").classList.toggle("hidden", !show);
  if(show){
    $("#rsvp-series-label").textContent =
      t("rsvp_series_label").replace("{state}", t("rsvp_"+currentYourState));
  }
}

/* Lot 6 : point d'entree UNIQUE pour PUT /api/presences -- reutilise par
   le contrôle RSVP (present/maybe/absent) ET par le sélecteur de
   préférences (aircraft/mission_types), pour toujours envoyer le `state`
   requis par l'API même quand seules les préférences changent. */
async function putPresence(state, opts){
  const eventId = currentModalEventId, occDate = currentModalOccDate;
  const body = {event_id:eventId, occ_date:occDate, state};
  if(rsvpPrefsVisible){
    body.aircraft = prefsAircraft;
    body.mission_types = prefsMissionTypes;
  }
  try {
    await apiFetch("/api/presences", {
      method:"PUT",
      headers:{"Content-Type":"application/json"},
      body: JSON.stringify(body)
    });
    if(!opts || !opts.silent) showToast(t("rsvp_"+state)+" ✓");
    // Le compteur affiché dans la Planche (presence_counts) sera rafraîchi
    // par l'"invalidate" SSE qui suit ce PUT — pas d'incrément local ici.
  } catch(e){
    showToast(t("error_generic"), "erreur");
  }
}

/* Preferences RSVP (Lot 6) : n'enregistre que si un état RSVP existe déjà
   (present/maybe/absent) -- le champ `state` est obligatoire côté API ;
   tant que l'utilisateur n'a pas RSVP'é, la sélection reste locale. */
function savePrefs(){
  if(!currentYourState) return;
  putPresence(currentYourState, {silent:true});
}

/* Lot R3 §A3 : visibilité des préférences RSVP pilotée par le TYPE *et* la
   réponse RSVP courante (present/maybe) -- masquées si absent/pas de réponse.
   Appelée à l'ouverture (renderModalView, forcePopulate=true : roster frais,
   toujours repeuplé) et après chaque clic RSVP (renderRsvpControl, sans
   forcePopulate : ne peuple que si la visibilité vient de basculer false→true,
   pour ne pas écraser une sélection en cours si l'état ne change pas).
   Remplace l'ancienne renderRsvpPrefs(occ, roster) -- lit currentModalOccurrence
   à la place, currentModalOccurrence étant déjà à jour à chaque site d'appel. */
function updatePrefsVisibility(forcePopulate){
  const occ = currentModalOccurrence;
  if(!occ) return;
  const wasVisible = rsvpPrefsVisible;
  rsvpPrefsVisible = PREFS_EVENT_TYPES.has(occ.type)
                     && (currentYourState === "present" || currentYourState === "maybe");
  $("#rsvp-prefs").classList.toggle("hidden", !rsvpPrefsVisible);
  if(!rsvpPrefsVisible){
    prefsAircraft = [];
    prefsMissionTypes = [];
    return;
  }
  if(!wasVisible || forcePopulate){
    // Pré-remplissage depuis SA PROPRE entrée du roster (le backend expose
    // aircraft/mission_types par pilote, y compris pour l'utilisateur courant).
    const roster = occ.roster || {present:[], maybe:[], absent:[]};
    let mine = null;
    ["present","maybe","absent"].forEach(st=>{
      (roster[st]||[]).forEach(p=>{ if(ME && String(p.profile_id)===String(ME.id)) mine = p; });
    });
    prefsAircraft = (mine && mine.aircraft) ? mine.aircraft.slice() : [];
    prefsMissionTypes = (mine && mine.mission_types) ? mine.mission_types.slice() : [];
    renderAircraftChips();
    renderAircraftOptions();
    renderMissionChips();
    $("#aircraft-dropdown").classList.add("hidden");
  }
}

function renderAircraftChips(){
  const wrap = $("#aircraft-chips");
  wrap.innerHTML = prefsAircraft.map(code=>`
    <span class="chip-picker-chip">${escapeHtml(code)}<button type="button" class="chip-picker-chip-remove" aria-label="×" data-code="${escapeAttr(code)}">×</button></span>
  `).join("");
  $$(".chip-picker-chip-remove", wrap).forEach(btn=>{
    btn.addEventListener("click", ()=>{
      const code = btn.dataset.code;
      prefsAircraft = prefsAircraft.filter(c=>c!==code);
      renderAircraftChips();
      renderAircraftOptions();
      savePrefs();
    });
  });
}

function renderAircraftOptions(){
  const filterVal = ($("#aircraft-filter").value||"").trim().toLowerCase();
  const wrap = $("#aircraft-options");
  const filtered = AIRCRAFT_CODES.filter(c=> c.toLowerCase().includes(filterVal));
  if(filtered.length===0){
    wrap.innerHTML = `<div class="chip-picker-empty">${escapeHtml(t("pref_no_match"))}</div>`;
    return;
  }
  wrap.innerHTML = filtered.map(code=>{
    const sel = prefsAircraft.includes(code);
    return `<button type="button" class="chip-picker-option${sel?" sel":""}" role="option" aria-selected="${sel}" data-code="${escapeAttr(code)}">${escapeHtml(code)}</button>`;
  }).join("");
  $$(".chip-picker-option", wrap).forEach(btn=>{
    btn.addEventListener("click", ()=>{
      const code = btn.dataset.code;
      if(prefsAircraft.includes(code)){
        prefsAircraft = prefsAircraft.filter(c=>c!==code);
      } else {
        prefsAircraft.push(code);
      }
      renderAircraftChips();
      renderAircraftOptions();
      savePrefs();
    });
  });
}

/* Jeu libre (Lot 8) : sélecteur mono-choix, même patron visuel que le
   sélecteur d'appareils (.chip-picker) mais un seul choix possible --
   sélectionner une option remplace la précédente et referme le menu. */
function renderGameChips(){
  const wrap = $("#game-chips");
  if(!wrap) return;
  wrap.innerHTML = gameSelected ? `
    <span class="chip-picker-chip">${escapeHtml(gameLabelDisplay(gameSelected))}<button type="button" class="chip-picker-chip-remove" aria-label="×" data-clear="1">×</button></span>
  ` : "";
  const removeBtn = $(".chip-picker-chip-remove", wrap);
  if(removeBtn) removeBtn.addEventListener("click", ()=>{
    gameSelected = null;
    gameOtherText = "";
    renderGameChips();
    renderGameOptions();
    toggleGameOtherInput();
  });
}

function renderGameOptions(){
  const filterEl = $("#game-filter");
  const filterVal = (filterEl ? filterEl.value : "").trim().toLowerCase();
  const wrap = $("#game-options");
  if(!wrap) return;
  const typeSel = $("#f-type");
  const typeVal = typeSel ? typeSel.value : "mission";
  // v0.26 : structuré -> plateforme fermée (pas de "autre") ; jeulibre ->
  // liste FREE_PLAY_GAMES + sentinel "autre".
  const src = isStructuredType(typeVal) ? STRUCTURED_GAMES : FREE_PLAY_GAMES.concat([GAME_OTHER_VALUE]);
  const filtered = src.filter(code=> gameLabelDisplay(code).toLowerCase().includes(filterVal));
  if(filtered.length===0){
    wrap.innerHTML = "";
    return;
  }
  wrap.innerHTML = filtered.map(code=>{
    const sel = gameSelected === code;
    return `<button type="button" class="chip-picker-option${sel?" sel":""}" role="option" aria-selected="${sel}" data-code="${escapeAttr(code)}">${escapeHtml(gameLabelDisplay(code))}</button>`;
  }).join("");
  $$(".chip-picker-option", wrap).forEach(btn=>{
    btn.addEventListener("click", ()=>{
      gameSelected = btn.dataset.code;
      if(gameSelected !== GAME_OTHER_VALUE) gameOtherText = "";
      renderGameChips();
      renderGameOptions();
      syncGamePlatformUI();
      const dd = $("#game-dropdown");
      if(dd) dd.classList.add("hidden");
    });
  });
}

function toggleGameOtherInput(){
  const inp = $("#f-game-other");
  if(!inp) return;
  const typeSel = $("#f-type");
  const typeVal = typeSel ? typeSel.value : "mission";
  // v0.26 : l'input "autre" n'existe/ne s'affiche QUE pour jeulibre.
  const show = !isStructuredType(typeVal) && gameSelected === GAME_OTHER_VALUE;
  inp.classList.toggle("hidden", !show);
}

/* v0.26 : resynchronise l'UI plateforme/map après un changement de type
   ou une sélection de jeu -- libellé de la game row, présence de l'input
   "autre", visibilité de la map row (structuré && plateforme === DCS). */
function syncGamePlatformUI(){
  const typeSel = $("#f-type");
  const typeVal = typeSel ? typeSel.value : "mission";
  const structured = isStructuredType(typeVal);
  const labelEl = $("#f-game-row-label");
  if(labelEl) labelEl.textContent = structured ? t('field_platform') : t('field_game');
  toggleGameOtherInput();
  const showMap = structured && gameSelected === "DCS";
  const mapRow = $("#f-map-row");
  if(mapRow){
    mapRow.classList.toggle("hidden", !showMap);
    if(!showMap && mapSelected){
      mapSelected = null;
      renderMapChips();
      renderMapOptions();
    }
  }
}

/* Valeur résolue à la soumission (Point 3) : jeu nommé, texte "autre", ou
   null. Remplace la lecture directe de #f-game.value (ancien champ texte). */
function resolveGameLabelForSubmit(){
  if(!gameSelected) return null;
  if(gameSelected === GAME_OTHER_VALUE){
    const inp = $("#f-game-other");
    const txt = (inp ? inp.value : "").trim();
    return txt || null;
  }
  return gameSelected;
}

/* v0.23 : map (Mission/Entraînement) -- même patron visuel que le
   sélecteur de jeu (.chip-picker mono-choix), mais liste FERMÉE : pas de
   sentinel "autre", donc pas de champ texte associé. */
function renderMapChips(){
  const wrap = $("#map-chips");
  if(!wrap) return;
  wrap.innerHTML = mapSelected ? `
    <span class="chip-picker-chip">${escapeHtml(mapSelected)}<button type="button" class="chip-picker-chip-remove" aria-label="×" data-clear="1">×</button></span>
  ` : "";
  const removeBtn = $(".chip-picker-chip-remove", wrap);
  if(removeBtn) removeBtn.addEventListener("click", ()=>{
    mapSelected = null;
    renderMapChips();
    renderMapOptions();
  });
}

function renderMapOptions(){
  const filterEl = $("#map-filter");
  const filterVal = (filterEl ? filterEl.value : "").trim().toLowerCase();
  const wrap = $("#map-options");
  if(!wrap) return;
  const filtered = MAPS.filter(name=> name.toLowerCase().includes(filterVal));
  if(filtered.length===0){
    wrap.innerHTML = `<div class="chip-picker-empty">${escapeHtml(t("pref_no_match"))}</div>`;
    return;
  }
  wrap.innerHTML = filtered.map(name=>{
    const sel = mapSelected === name;
    return `<button type="button" class="chip-picker-option${sel?" sel":""}" role="option" aria-selected="${sel}" data-code="${escapeAttr(name)}">${escapeHtml(name)}</button>`;
  }).join("");
  $$(".chip-picker-option", wrap).forEach(btn=>{
    btn.addEventListener("click", ()=>{
      mapSelected = btn.dataset.code;
      renderMapChips();
      renderMapOptions();
      const dd = $("#map-dropdown");
      if(dd) dd.classList.add("hidden");
    });
  });
}

/* Valeur résolue à la soumission : nom de map exact (MAPS) ou null. Pas
   d'équivalent "autre" (liste fermée, cf. brief v0.23). */
function resolveMapSelection(){
  return mapSelected || null;
}

function renderMissionChips(){
  const wrap = $("#mission-chips");
  wrap.innerHTML = MISSION_TYPES.map(m=>{
    const sel = prefsMissionTypes.includes(m.code);
    return `<button type="button" class="mission-chip${sel?" on":""}" data-code="${m.code}">${escapeHtml(missionLabel(m.code))}</button>`;
  }).join("");
  $$(".mission-chip", wrap).forEach(btn=>{
    btn.addEventListener("click", ()=>{
      const code = btn.dataset.code;
      if(prefsMissionTypes.includes(code)){
        prefsMissionTypes = prefsMissionTypes.filter(c=>c!==code);
      } else {
        prefsMissionTypes.push(code);
      }
      renderMissionChips();
      savePrefs();
    });
  });
}

function renderRoster(roster){
  const wrap = $("#roster-groups"); wrap.innerHTML="";
  ["present","maybe","absent"].forEach(st=>{
    const list = roster[st]||[];
    if(list.length===0) return;
    const block=document.createElement("div");
    const entries = list.map(p=>{
      const isYou = ME && String(p.profile_id)===String(ME.id);
      const squadronHtml = p.squadron ? `<span class="roster-squadron">· ${escapeHtml(p.squadron)}</span>` : "";
      const prefsHtml = rosterPrefsHtml(p);
      return `<div class="roster-entry">
        <span class="roster-pill"><span class="avatar">${avatarHtml(p.profile_id, p.avatar_hash, p.name)}</span>${escapeHtml(callsign(p.name))}${squadronHtml}</span>
        ${prefsHtml}
      </div>`;
    }).join("");
    block.innerHTML = `<div class="roster-group-label" style="color:var(--rsvp-${st})"><span>${pip(st)}</span>${t('rsvp_'+st)}<span class="roster-group-count" style="--roster-count-color:var(--rsvp-${st})">${list.length}</span></div>
      <div class="roster-avatars">${entries}</div>`;
    wrap.appendChild(block);
  });
}

/* Lot 6 : petites puces "muettes" (appareils + missions) affichées sous
   chaque pilote présent/peut-être dans le roster (SPEC B.5). */
function rosterPrefsHtml(p){
  const chips = [];
  (p.aircraft||[]).forEach(code=> chips.push(`<span class="roster-pref-chip">${escapeHtml(code)}</span>`));
  (p.mission_types||[]).forEach(code=> chips.push(`<span class="roster-pref-chip">${escapeHtml(missionLabel(code))}</span>`));
  if(chips.length===0) return "";
  return `<div class="roster-prefs">${chips.join("")}</div>`;
}

function closeModal(){
  if(rrConfirmCourante) rrConfirmCourante(false);   // Lot « La charte commune de l'App » (v1.0079)
  $("#modal-overlay").classList.add("hidden");
  currentModalEventId = null;
  currentModalOccDate = null;
  currentModalMode = null;
  currentModalOccurrence = null;
  currentDayDate = null;
  pendingEditScope = "series";
  ficheSoireeNeuve();   // Lot « Les liens de la soirée » (v1.0107) : la fiche fermée, une réponse en retard est ignorée
  marquerOuverte();   // Lot « La Planification en grand écran » (v1.0077) : plus rien n'est cerclé
  rrFenetreFermee("overlay");   // Lot « Le retour et l'adresse » (v1.0101) : la fermer, par n'importe quel chemin, consomme son entrée
}

/* ---------- Modale : synthèse du jour (Lot C) ---------- */
/* Lot R3 §B1 : en-tête "bloc-notes" -- jour de semaine (type-label) + date
   en toutes lettres (title), pour qu'on lise "c'est une journée" au premier
   coup d'oeil, visuellement distinct d'un titre d'event. Remplace l'ancien
   fmtDayReadable (titre plat unique), scindé en deux pour cibler les deux
   zones de l'en-tête séparément. */
function fmtDayWeekday(dateStr){
  const [y,m,d] = dateStr.split("-").map(Number);
  const jsDow = new Date(y, m-1, d).getDay();
  return WEEKDAYS_FULL[currentLang][(jsDow+6)%7].toUpperCase();
}
function fmtDayDateLabel(dateStr){
  const [y,m,d] = dateStr.split("-").map(Number);
  return `${d} ${MONTHS[currentLang][m-1]}`;
}

/* Puces compactes présents/peut-être pour une carte-event de la synthèse
   du jour — même patron visuel que renderRoster (roster-pill/avatar), mais
   sans squadron/prefs (compact) et sans groupe ABSENT (hors périmètre ici). */
function dayRosterHtml(roster){
  const groups = ["present","maybe"].map(st=>{
    const list = (roster && roster[st]) || [];
    if(list.length===0) return "";
    const pills = list.map(p=>{
      const isYou = ME && String(p.profile_id)===String(ME.id);
      return `<span class="roster-pill day-roster-pill-${st}"><span class="avatar">${avatarHtml(p.profile_id, p.avatar_hash, p.name)}</span>${escapeHtml(callsign(p.name))}</span>`;
    }).join("");
    return pills;
  }).join("");
  if(!groups) return "";
  return `<div class="day-roster">${groups}</div>`;
}

/* Carte détaillée (occurrence chargée avec roster). */
function dayEventCardFull(occ){
  const sub = [occ.game_label, occ.map_name].filter(Boolean).join(" · ");
  return `
    <div class="day-event-card" data-event-id="${occ.event_id}" data-occ-date="${occ.occ_date}" style="--chip-color:var(${TYPE_VAR[occ.type]})">
      <div class="day-event-head">
        <span class="ico">${TYPE_ICON[occ.type]}</span>
        <span>${escapeHtml(occ.title)}${newTag(occ)}</span>
        <span style="margin-left:auto;font-family:var(--font-mono);font-size:.76rem;color:var(--text-mute);">${fmtLocalTime(occ.start_at_utc)}</span>
      </div>
      ${sub? `<div class="day-event-sub">${escapeHtml(sub)}</div>` : ""}
      ${dayRosterHtml(occ.roster)}
    </div>`;
}

/* Carte de repli (le fetch détail a échoué pour cette occurrence) : mêmes
   infos qu'une puce de grille (presence_counts du mois), sans les noms —
   ne casse pas le reste de la liste (brief §ÉTAPE 2). */
function dayEventCardFallback(occ){
  const sub = [occ.game_label, occ.map_name].filter(Boolean).join(" · ");
  const counts = occ.presence_counts || {present:0, maybe:0};
  return `
    <div class="day-event-card" data-event-id="${occ.event_id}" data-occ-date="${occ.occ_date}" style="--chip-color:var(${TYPE_VAR[occ.type]})">
      <div class="day-event-head">
        <span class="ico">${TYPE_ICON[occ.type]}</span>
        <span>${escapeHtml(occ.title)}${newTag(occ)}</span>
        <span style="margin-left:auto;font-family:var(--font-mono);font-size:.76rem;color:var(--text-mute);">${fmtLocalTime(occ.start_at_utc)}</span>
      </div>
      ${sub? `<div class="day-event-sub">${escapeHtml(sub)}</div>` : ""}
      <div class="day-event-sub"><b style="color:var(--rsvp-present)">${counts.present} ✓</b> · <i style="color:var(--rsvp-maybe)">${counts.maybe} ~</i></div>
    </div>`;
}

/* Rendu du corps de la modale jour : liste de cartes (ou message vide) +
   bouton "+ Créer ce jour" (gated event.create), toujours à la fin. */
function renderDayModalBody(dateStr, occs, details){
  const cards = occs.map((o, i)=>{
    const full = details ? details[i] : null;
    return full ? dayEventCardFull(full) : dayEventCardFallback(o);
  }).join("");

  // Lot R3 §B2 : bouton créer ancré en tête (avant les cartes), visible sans dérouler.
  const createBtn = (ME && (ME.capabilities||[]).includes("event.create"))
    ? `<button type="button" id="day-create-btn" class="btn btn-accent btn-sm" style="margin-bottom:.8rem;">${t("day_create")}</button>`
    : "";

  const empty = occs.length===0
    ? `<div style="padding:.4rem 0 .8rem;color:var(--text-mute);">${t("day_no_events")}</div>`
    : "";

  $("#modal-desc").innerHTML = createBtn + empty + cards;

  $$(".day-event-card", $("#modal-desc")).forEach(card=>{
    card.addEventListener("click", ()=> openEventModal(card.dataset.eventId, card.dataset.occDate));
  });
  const btn = $("#day-create-btn");
  if(btn) btn.addEventListener("click", ()=> openCreateModal(dateStr));
}

async function openDayModal(dateStr){
  currentModalMode = "day";
  currentDayDate = dateStr;
  currentModalEventId = null;
  currentModalOccDate = null;
  currentModalOccurrence = null;

  $("#modal-accent-bar").style.setProperty("--modal-accent", "var(--accent)"); // Lot R3 §A1
  $("#modal-type-ico").innerHTML = "";
  $("#modal-type-label").textContent = fmtDayWeekday(dateStr); // Lot R3 §B1
  $("#modal-type-label").style.color = "var(--accent)";
  $("#modal-title").textContent = fmtDayDateLabel(dateStr); // Lot R3 §B1
  $("#modal-datetime").innerHTML = "";
  $("#modal-presence-summary").innerHTML = ""; // Lot R3 §A2 -- hors périmètre en vue Jour
  ficheSoireeNeuve();   // Lot « Les liens de la soirée » (v1.0107)
  $("#modal-creator").textContent = "";
  $("#modal-rsvp-section").classList.add("hidden");
  $("#modal-roster-section").classList.add("hidden");
  $("#modal-edit-btn").classList.add("hidden");
  $("#modal-delete-btn").classList.add("hidden");
  $("#modal-save-btn").classList.add("hidden");
  $("#recurrence-note").classList.add("hidden");
  $("#modal-desc").innerHTML = `<div style="padding:1rem 0;color:var(--text-mute);">${t("loading")}</div>`;
  $("#rsvp-prefs").classList.add("hidden"); // Correctif R6 §1 : fuite fix R3.1
  showModalShell({t:"jour", date:dateStr});

  const occs = eventsForDate(dateStr);
  if(occs.length===0){
    renderDayModalBody(dateStr, []);
    return;
  }

  const details = await Promise.all(occs.map(o=>
    apiFetch(`/api/events/${o.event_id}/occurrences/${o.occ_date}`).catch(()=> null)
  ));
  // Garde anti-course : si la modale a été fermée ou qu'une autre date a
  // été ouverte entre-temps, on n'écrase pas l'affichage courant.
  if(currentModalMode !== "day" || currentDayDate !== dateStr) return;
  renderDayModalBody(dateStr, occs, details);
}

/* ---------- Modale : création / édition ---------- */
/* `prefill` accepte, en plus des champs simples, `date`/`time` (édition
   série, Lot 4 §1), `recurring`/`weekdays`/`interval`/`endType`/`endUntil`/
   `endCount` pour pré-remplir intégralement une récurrence existante. */
function buildEventFormHTML(prefill, withDateRecurrence){
  const p = prefill || {};
  const type = p.type || "mission";

  // Correctif R6 §4 : formulaire regroupé en 3 groupes -- Quoi / Quand /
  // Récurrence (décision du porteur, remplace Général/Quand/Plateforme/Détails
  // de L4). Mapping verrouillé (brief) : tous les IDs et le câblage
  // wireEventFormConditionals restent identiques -- seuls les conteneurs de
  // groupe et leur ordre changent.

  const structured = isStructuredType(type);
  const gameState = resolveGameSelection(p.game_label, type);
  gameSelected = gameState.selected;
  gameOtherText = gameState.otherText;
  // v0.26 : plateforme structurée -- défaut "DCS" si aucune valeur valide.
  if(structured && !gameSelected) gameSelected = "DCS";
  // map -- pertinente seulement si plateforme structurée == DCS.
  const showMapRow = structured && gameSelected === "DCS";
  mapSelected = (showMapRow && p.map_name && MAPS.includes(p.map_name)) ? p.map_name : null;
  const showGameOther = !structured && gameSelected === GAME_OTHER_VALUE;

  // --- Groupe "Quoi" : titre · type · durée · jeu/plateforme · carte · description ---
  let html = `
    <div class="form-group">
      <div class="form-group-title">${t('form_group_quoi')}</div>
      <div class="form-field"><label>${t('field_title')}</label><input type="text" id="f-title" maxlength="120" value="${escapeAttr(p.title||"")}" placeholder="${t('field_title')}"></div>
      <div class="form-row">
        <div class="form-field"><label>${t('field_type')}</label>
          <select id="f-type">
            <option value="entrainement"${type==="entrainement"?" selected":""}>${t('type_entrainement')}</option>
            <option value="mission"${type==="mission"?" selected":""}>${t('type_mission')}</option>
            <option value="campagne"${type==="campagne"?" selected":""}>${t('type_campagne')}</option>
            <option value="jeulibre"${type==="jeulibre"?" selected":""}>${t('type_jeulibre')}</option>
          </select>
        </div>
        <div class="form-field"><label>${t('field_duration')}</label><input type="number" min="1" max="1440" id="f-duration" value="${p.duration_min||""}" placeholder="90"></div>
      </div>
      <div class="form-field" id="f-game-row">
        <label id="f-game-row-label">${structured ? t('field_platform') : t('field_game')}</label>
        <div id="game-picker" class="chip-picker">
          <div class="chip-picker-input">
            <div id="game-chips" class="chip-picker-chips"></div>
            <button type="button" id="game-add-btn" class="chip-picker-add-btn" aria-haspopup="listbox">${t('pref_add')}</button>
          </div>
          <div id="game-dropdown" class="chip-picker-dropdown hidden">
            <input type="text" id="game-filter" class="chip-picker-filter" placeholder="${t('pref_filter_ph')}" autocomplete="off">
            <div id="game-options" class="chip-picker-options" role="listbox"></div>
          </div>
        </div>
        <input type="text" id="f-game-other" maxlength="60" class="${showGameOther?"":"hidden"}" style="margin-top:.5rem;" value="${escapeAttr(gameOtherText)}" placeholder="${t('field_game')}">
      </div>
      <div class="form-field${showMapRow?"":" hidden"}" id="f-map-row">
        <label>${t('field_map')}</label>
        <div id="map-picker" class="chip-picker">
          <div class="chip-picker-input">
            <div id="map-chips" class="chip-picker-chips"></div>
            <button type="button" id="map-add-btn" class="chip-picker-add-btn" aria-haspopup="listbox">${t('pref_add')}</button>
          </div>
          <div id="map-dropdown" class="chip-picker-dropdown hidden">
            <input type="text" id="map-filter" class="chip-picker-filter" placeholder="${t('pref_filter_ph')}" autocomplete="off">
            <div id="map-options" class="chip-picker-options" role="listbox"></div>
          </div>
        </div>
      </div>
      <div class="form-field"><label>${t('field_desc')}</label><textarea rows="3" id="f-desc" maxlength="4000" placeholder="${t('field_desc')}">${escapeHtml(p.description||"")}</textarea></div>
    </div>`;

  // --- Groupe "Quand" : date · heure (portée SÉRIE uniquement) ---
  // --- Groupe "Récurrence" : case f-recurring + options (portée SÉRIE uniquement) ---
  if(withDateRecurrence){
    const recurring = !!p.recurring;
    const weekdays = p.weekdays || [];
    const interval = p.interval || 1;
    const endType = p.endType || "none";
    html += `
    <div class="form-group">
      <div class="form-group-title">${t('form_group_quand')}</div>
      <div class="form-row form-row-inline">
        <div class="form-field"><label>${t('field_date')}</label><input type="date" id="f-date" value="${escapeAttr(p.date||"")}"></div>
        <div class="form-field"><label>${t('field_time')}</label><input type="time" id="f-time" value="${escapeAttr(p.time||"21:00")}"></div>
      </div>
    </div>
    <div class="form-group">
      <div class="form-group-title">${t('form_group_recurrence')}</div>
      <div class="form-field field-checkbox">
        <label><input type="checkbox" id="f-recurring"${recurring?" checked":""}> ${t('field_recurring')}</label>
      </div>
      <div id="f-recurrence-panel" class="${recurring?"":"hidden"}">
        <div class="form-field"><label>${t('field_weekdays')}</label>
          <div class="filter-chips weekday-toggle">${WEEKDAY_KEYS.map(i=>`<button type="button" class="chip-filter${weekdays.includes(i)?" on":""}" data-day="${i}">${WEEKDAYS[currentLang][i]}</button>`).join("")}</div>
        </div>
        <div class="form-row">
          <div class="form-field"><label>${t('field_interval')}</label><input type="number" min="1" max="52" id="f-interval" value="${interval}"></div>
          <div class="form-field"><label>${t('field_end')}</label>
            <select id="f-end-type">
              <option value="none"${endType==="none"?" selected":""}>${t('end_none')}</option>
              <option value="until"${endType==="until"?" selected":""}>${t('end_until')}</option>
              <option value="count"${endType==="count"?" selected":""}>${t('end_count')}</option>
            </select>
          </div>
        </div>
        <div class="form-row">
          <div class="form-field${endType==="until"?"":" hidden"}" id="f-end-until-row"><label>${t('end_until')}</label><input type="date" id="f-end-until" value="${escapeAttr(p.endUntil||"")}"></div>
          <div class="form-field${endType==="count"?"":" hidden"}" id="f-end-count-row"><label>${t('end_count')}</label><input type="number" min="1" max="500" id="f-end-count" value="${p.endCount||10}"></div>
        </div>
      </div>
    </div>`;
  }

  return html;
}

function wireEventFormConditionals(){
  const typeSel = $("#f-type");
  if(typeSel) typeSel.addEventListener("change", ()=>{
    const typeVal = typeSel.value;
    const structured = isStructuredType(typeVal);
    // Reconstruit le picker jeu pour le nouveau type : conserve la
    // sélection courante si elle reste valide dans le nouveau contexte,
    // sinon défaut "DCS" (structuré) ou vide (jeulibre).
    if(structured){
      if(!STRUCTURED_GAMES.includes(gameSelected)) gameSelected = "DCS";
    } else if(gameSelected !== GAME_OTHER_VALUE && !FREE_PLAY_GAMES.includes(gameSelected)){
      gameSelected = null;
      gameOtherText = "";
    }
    renderGameChips();
    renderGameOptions();
    syncGamePlatformUI();
  });
  // Lot 8 : sélecteur mono-choix jeu libre. La modale est régénérée à
  // chaque ouverture (buildEventFormHTML) donc ce câblage est local à
  // l'instance courante -- pas de listener empilé (cf. fermeture globale
  // du dropdown, gérée une seule fois dans wireStaticUI).
  const gameAddBtn = $("#game-add-btn");
  if(gameAddBtn){
    gameAddBtn.addEventListener("click", ()=>{
      const dd = $("#game-dropdown");
      const willOpen = dd.classList.contains("hidden");
      dd.classList.toggle("hidden");
      if(willOpen){
        $("#game-filter").value = "";
        renderGameOptions();
        $("#game-filter").focus();
      }
    });
    $("#game-filter").addEventListener("input", ()=> renderGameOptions());
    renderGameChips();
    renderGameOptions();
    toggleGameOtherInput();
  }
  // v0.23 : sélecteur map (même patron, liste fermée).
  const mapAddBtn = $("#map-add-btn");
  if(mapAddBtn){
    mapAddBtn.addEventListener("click", ()=>{
      const dd = $("#map-dropdown");
      const willOpen = dd.classList.contains("hidden");
      dd.classList.toggle("hidden");
      if(willOpen){
        $("#map-filter").value = "";
        renderMapOptions();
        $("#map-filter").focus();
      }
    });
    $("#map-filter").addEventListener("input", ()=> renderMapOptions());
    renderMapChips();
    renderMapOptions();
  }
  const recurCk = $("#f-recurring");
  if(recurCk) recurCk.addEventListener("change", ()=>{
    $("#f-recurrence-panel").classList.toggle("hidden", !recurCk.checked);
  });
  $$(".weekday-toggle button").forEach(b=> b.addEventListener("click", ()=> b.classList.toggle("on")));
  const endSel = $("#f-end-type");
  if(endSel) endSel.addEventListener("change", ()=>{
    $("#f-end-until-row").classList.toggle("hidden", endSel.value !== "until");
    $("#f-end-count-row").classList.toggle("hidden", endSel.value !== "count");
  });
}

function openCreateModal(prefillDate){
  currentModalMode = "create";
  currentModalEventId = null; currentModalOccDate = null; currentModalOccurrence = null;

  $("#modal-accent-bar").style.setProperty("--modal-accent", "var(--type-mission)"); // Lot R3 §A1
  $("#modal-type-ico").innerHTML = TYPE_ICON["mission"];
  $("#modal-type-ico").style.setProperty("--chip-color", "var(--type-mission)");
  $("#modal-type-label").textContent = t("new_event_title");
  $("#modal-type-label").style.color = "var(--type-mission)";
  $("#modal-title").textContent = "";
  $("#modal-datetime").innerHTML = "";
  $("#modal-presence-summary").innerHTML = ""; // Lot R3 §A2 -- hors périmètre en création
  ficheSoireeNeuve();   // Lot « Les liens de la soirée » (v1.0107)
  // Lot 4 §3 : date pré-remplie quand la modale est ouverte depuis un clic
  // sur une case-date du calendrier (sinon champ vide, comportement inchangé).
  $("#modal-desc").innerHTML = buildEventFormHTML(prefillDate ? {date: prefillDate} : null, true);
  wireEventFormConditionals();
  $("#modal-creator").textContent = "";
  $("#modal-rsvp-section").classList.add("hidden");
  $("#rsvp-prefs").classList.add("hidden"); // Correctif R6 §1 : fuite fix R3.1
  $("#modal-roster-section").classList.add("hidden");
  $("#recurrence-note").classList.add("hidden");
  $("#modal-edit-btn").classList.add("hidden");
  $("#modal-delete-btn").classList.add("hidden");
  $("#modal-save-btn").classList.remove("hidden");
  showModalShell({t:"creation", date: typeof prefillDate === "string" ? prefillDate : null});
}

async function openEditModal(scope){
  currentModalMode = "edit";
  pendingEditScope = scope;
  const occ = currentModalOccurrence;
  const eventId = currentModalEventId;

  $("#modal-accent-bar").style.setProperty("--modal-accent", `var(${TYPE_VAR[occ.type]})`); // Lot R3 §A1
  $("#modal-type-ico").innerHTML = TYPE_ICON[occ.type];
  $("#modal-type-ico").style.setProperty("--chip-color", `var(${TYPE_VAR[occ.type]})`);
  $("#modal-type-label").textContent = t("edit_event_title");
  $("#modal-type-label").style.color = `var(${TYPE_VAR[occ.type]})`;
  $("#modal-title").textContent = "";
  $("#modal-datetime").innerHTML = "";
  $("#modal-presence-summary").innerHTML = ""; // Lot R3 §A2 -- hors périmètre en édition
  ficheSoireeCacher();   // Lot « Les liens de la soirée » (v1.0107) : cachée en édition, la lecture faite reste à la fiche
  $("#modal-creator").textContent = "";
  $("#modal-rsvp-section").classList.add("hidden");
  $("#rsvp-prefs").classList.add("hidden"); // Correctif R6 §1 : fuite fix R3.1
  $("#modal-roster-section").classList.add("hidden");
  $("#recurrence-note").classList.add("hidden");
  $("#modal-edit-btn").classList.add("hidden");
  $("#modal-delete-btn").classList.add("hidden");
  $("#modal-save-btn").classList.remove("hidden");

  const withDateRecurrence = scope === "series";
  const prefill = {
    type: occ.type, game_label: occ.game_label, map_name: occ.map_name, title: occ.title,
    description: occ.description, duration_min: occ.duration_min
  };

  if(withDateRecurrence){
    // Édition en portée SÉRIE (Lot 4 §1) : date/heure/récurrence viennent
    // de l'Event brut (GET /api/events/{id}), jamais de l'occurrence
    // effective. En portée "occurrence" ces champs restent absents du
    // formulaire (hors périmètre : pas d'édition de date pour une seule
    // occurrence, cf. brief).
    $("#modal-desc").innerHTML = `<div style="padding:1rem 0;color:var(--text-mute);">${t("loading")}</div>`;
    showModalShell({t:"edition", ev:eventId, date:currentModalOccDate, portee:scope});
    let seriesEvent;
    try {
      seriesEvent = await apiFetch(`/api/events/${eventId}`);
    } catch(e){
      showToast(t("error_generic"), "erreur");
      closeModal();
      return;
    }
    const localDt = new Date(seriesEvent.start_at);
    prefill.date = toISODate(localDt);
    prefill.time = `${pad2(localDt.getHours())}:${pad2(localDt.getMinutes())}`;
    const rec = seriesEvent.recurrence;
    if(rec){
      prefill.recurring = true;
      prefill.weekdays = rec.weekdays || [];
      prefill.interval = rec.interval || 1;
      if(rec.end && rec.end.type === "until"){
        prefill.endType = "until"; prefill.endUntil = rec.end.until;
      } else if(rec.end && rec.end.type === "count"){
        prefill.endType = "count"; prefill.endCount = rec.end.count;
      } else {
        prefill.endType = "none";
      }
    }
  }

  $("#modal-desc").innerHTML = buildEventFormHTML(prefill, withDateRecurrence);
  wireEventFormConditionals();
  showModalShell({t:"edition", ev:eventId, date:currentModalOccDate, portee:scope});
}

/* Après une mutation propre (création/édition/suppression), on rafraîchit
   toujours la vue calendrier courante, et le hebdo directement s'il est la
   vue active — sinon on le marque périmé pour un refetch au changement
   d'onglet (même logique que flushRefetch, cf. Lot 4 §4). */
async function afterMutationRefresh(){
  await refreshCurrentCalendarView();
  if(currentAppView === "hebdo"){
    await refreshHebdo();
  } else {
    hebdoStale = true;
  }
}

async function submitEventForm(){
  const title = $("#f-title").value.trim();
  if(!title){ showToast(t("error_generic"), "erreur"); return; }
  const type = $("#f-type").value;
  const game_label = resolveGameLabelForSubmit();               // structuré=plateforme, jeulibre=libre/autre
  const map_name = (isStructuredType(type) && game_label === "DCS")
                   ? resolveMapSelection() : null;
  const description = $("#f-desc").value;
  const durationRaw = $("#f-duration").value;

  // Lot « Les finitions de l'édition » (v1.0103, ARC-16) : le corps porte toujours la durée — l'entier saisi, ou
  // `null` quand le champ est vide (un champ vidé retire la durée).
  const body = { type, game_label, map_name, title, description,
                 duration_min: durationRaw ? parseInt(durationRaw, 10) : null };

  // Date/heure/récurrence : présentes en DOM pour la création ET pour
  // l'édition en portée "série" (Lot 4 §1) — jamais en portée "occurrence"
  // (interdit côté API, cf. _SERIES_ONLY_FIELDS dans app/events.py).
  const includeDateRecurrence = currentModalMode === "create"
    || (currentModalMode === "edit" && pendingEditScope === "series");

  if(includeDateRecurrence){
    const dateVal = $("#f-date").value;
    const timeVal = $("#f-time").value || "21:00";
    if(!dateVal){ showToast(t("error_generic"), "erreur"); return; }
    const localDt = new Date(`${dateVal}T${timeVal}:00`);
    body.start_at = toISOStringWithOffset(localDt);

    if($("#f-recurring").checked){
      const weekdays = $$(".weekday-toggle button.on").map(b=> parseInt(b.dataset.day,10));
      if(weekdays.length === 0){ showToast(t("error_generic"), "erreur"); return; }
      const interval = parseInt($("#f-interval").value || "1", 10);
      const endType = $("#f-end-type").value;
      let end = null;
      if(endType === "until"){
        const untilVal = $("#f-end-until").value;
        if(!untilVal){ showToast(t("error_generic"), "erreur"); return; }
        // Lot « Les finitions de l'édition » (v1.0103, ARC-17) : une fin avant le premier jour s'arrête ici.
        if(untilVal < dateVal){ showToast(t("error_generic"), "erreur"); return; }
        end = {type:"until", until: untilVal};
      } else if(endType === "count"){
        const countVal = parseInt($("#f-end-count").value || "0", 10);
        if(!countVal || countVal < 1){ showToast(t("error_generic"), "erreur"); return; }
        end = {type:"count", count: countVal};
      }
      body.recurrence = { freq:"weekly", interval, weekdays, end };
    } else if(currentModalMode === "edit"){
      // Édition série, case décochée : annule explicitement une récurrence
      // existante (scope=series uniquement, jamais envoyé en scope=occurrence).
      body.recurrence = null;
    }
  }

  // Lot « Les finitions de l'édition » (v1.0103, ARC-14) : le bouton attend la réponse du serveur (pas de doublon
  // au double clic) ; réactivé quel que soit le résultat.
  const saveBtn = $("#modal-save-btn");
  if(currentModalMode === "create"){
    saveBtn.disabled = true;
    try {
      await apiFetch("/api/events", {method:"POST", headers:{"Content-Type":"application/json"}, body:JSON.stringify(body)});
      showToast(t("toast_created"));
      closeModal();
      await afterMutationRefresh();
    } catch(e){ showToast(t("error_generic"), "erreur"); }
    finally { saveBtn.disabled = false; }

  } else if(currentModalMode === "edit"){
    const scope = pendingEditScope;
    const qs = new URLSearchParams({scope});
    if(scope === "occurrence") qs.set("occ_date", currentModalOccDate);
    // Lot « La série juste » (v1.0104, ARC-19) : la version que l'éditeur a lue (l'`updated_at` de la série, porté
    // par la fiche ouverte) ; le serveur refuse l'enregistrement si l'évènement a changé depuis.
    const versionLue = currentModalOccurrence && currentModalOccurrence.event_updated_at;
    if(versionLue) qs.set("version", versionLue);
    const eventId = currentModalEventId;
    const patcher = ()=> apiFetch(`/api/events/${eventId}?${qs.toString()}`, {
      method:"PATCH", headers:{"Content-Type":"application/json"}, body:JSON.stringify(body)
    });
    saveBtn.disabled = true;
    let aEffacer = null;   // le 409 `reponses_a_effacer` : la note s'ouvre une fois le bouton rendu
    try {
      await patcher();
      showToast(t("toast_updated"));
      closeModal();
      await afterMutationRefresh();
    } catch(e){
      const code = e && e.detail && typeof e.detail === "object" ? e.detail.code : null;
      if(e && e.status === 409 && code === "reponses_a_effacer" && scope === "series") aEffacer = e.detail;
      else if(e && e.status === 409 && code === "modifie_entre_temps") await evenementModifieEntreTemps();
      else showToast(t("error_generic"), "erreur");
    }
    finally { saveBtn.disabled = false; }
    if(aEffacer){
      // Lot « La série juste » (v1.0104, ARC-15) : la note commune sous « Enregistrer » dit combien de réponses et de
      // dates à venir le changement efface ; son action rejoue le même PATCH avec `effacer=true`.
      const parts = [];
      if(aEffacer.reponses) parts.push(aEffacer.reponses === 1 ? t("serie_eff_rep_un") : t("serie_eff_rep_n").split("{n}").join(String(aEffacer.reponses)));
      if(aEffacer.dates) parts.push(aEffacer.dates === 1 ? t("serie_eff_date_un") : t("serie_eff_date_n").split("{n}").join(String(aEffacer.dates)));
      qs.set("effacer", "true");
      // Lot « La série juste » (v1.0104, addendum 1) : tant que la note est ouverte, « Enregistrer » reste grisé ;
      // une saisie dans la fiche ferme la note, pour qu'un corps corrigé ne parte jamais sous l'ancien.
      saveBtn.disabled = true;
      const fermerSurSaisie = ()=>{ if(rrConfirmCourante) rrConfirmCourante(false); };
      const formulaire = $("#modal-desc");
      formulaire.addEventListener("input", fermerSurSaisie);
      formulaire.addEventListener("change", fermerSurSaisie);
      const confirme = await rrConfirmer({
        ancre: saveBtn.closest(".modal-actions"), geste: saveBtn,
        titre: t("serie_eff_titre"), texte: t("serie_eff_texte").split("{liste}").join(parts.join(t("serie_eff_et"))),
        libelle: t("serie_eff_ok"), danger: true,
        action: async ()=>{
          try {
            await patcher();
          } catch(e){
            if(e && e.status === 409 && e.detail && e.detail.code === "modifie_entre_temps"){ await evenementModifieEntreTemps(); return; }
            throw e;
          }
          showToast(t("toast_updated"));
          closeModal();
          await afterMutationRefresh();
        }
      });
      formulaire.removeEventListener("input", fermerSurSaisie);
      formulaire.removeEventListener("change", fermerSurSaisie);
      saveBtn.disabled = false;
      if(!confirme && saveBtn.isConnected && !saveBtn.closest(".hidden")) saveBtn.focus();   // la note fermée rend le focus au geste
    }
  }
}

// Lot « La série juste » (v1.0104, ARC-19) : l'évènement a été modifié entre-temps — le message, la fiche se ferme,
// les vues se relisent ; rien n'a été écrit.
async function evenementModifieEntreTemps(){
  showToast(t("evt_modifie"), "erreur");
  closeModal();
  await afterMutationRefresh();
}

async function handleDelete(){
  const occ = currentModalOccurrence;
  if(!occ) return;
  // Lot « La charte commune de l'App » (v1.0079) : plus de boîte grise du navigateur — une note s'ouvre sous le bouton.
  const scope = occ.recurring ? $("#scope-select").value : "series";
  const eventId = currentModalEventId, occDate = currentModalOccDate;
  const qs = new URLSearchParams({scope});
  if(scope === "occurrence") qs.set("occ_date", occDate);
  const ro = occ.roster || {};
  const n = ["present","maybe","absent"].reduce((somme, st)=> somme + (ro[st] ? ro[st].length : 0), 0);
  const rep = n === 0 ? "" : (n === 1 ? t("confirm_rep_un") : t("confirm_rep_n").split("{n}").join(String(n)));
  let texte;
  if(!occ.recurring){
    texte = t("confirm_delete_seul").split("{rep}").join(rep);
  } else if(scope === "occurrence"){
    const jour = new Date(occ.occ_date + "T00:00:00").toLocaleDateString(currentLang === "en" ? "en-GB" : "fr-FR", {weekday:"long", day:"numeric", month:"long"});
    texte = t("confirm_delete_occ").split("{jour}").join(escapeHtml(jour)).split("{rep}").join(rep);
  } else {
    texte = t("confirm_delete_serie");
  }
  const geste = $("#modal-delete-btn");
  await rrConfirmer({
    ancre: geste.closest(".modal-actions"), geste,
    titre: t("confirm_delete"), texte, libelle: t("delete"), danger: true,
    action: async ()=>{
      await apiFetch(`/api/events/${eventId}?${qs.toString()}`, {method:"DELETE"});
      showToast(t("toast_deleted"));
      closeModal();
      await afterMutationRefresh();
    }
  });
}

/* ---------- Confirmation commune ----------
   Lot « La charte commune de l'App » (v1.0079) : une note sous le geste, qui dit ce qui disparaît et garde sa
   raison si le serveur refuse. `texte` est du HTML déjà sûr. Rend une Promise<bool>. */
let rrConfirmCourante = null;   // la fonction de fermeture de la note ouverte, ou null ; sa propriété `enCours` dit si l'action court
function rrConfirmer({ancre, geste, titre, texte, libelle, danger=false, action}){
  // Lot « La charte commune, au Débrief » (v1.0080, addendum 1) : une note dont l'action court ne se ferme pas de
  // l'extérieur ; le geste répété pendant l'appel n'ouvre rien (la promesse se résout `false` aussitôt).
  if(rrConfirmCourante){
    if(rrConfirmCourante.enCours) return Promise.resolve(false);
    rrConfirmCourante(false);
  }
  return new Promise(resolve=>{
    const note = document.createElement("div");
    note.className = "rr-confirm" + (danger ? " danger" : "");
    note.setAttribute("role", "group");
    note.setAttribute("aria-label", titre);
    note.innerHTML =
      `<div class="rr-confirm-titre">${escapeHtml(titre)}</div>` +
      `<div class="rr-confirm-texte">${texte}</div>` +
      `<div class="rr-confirm-err" role="alert" hidden></div>` +
      `<div class="rr-confirm-actions">` +
        `<button type="button" class="btn btn-sm" data-rr="annuler">${escapeHtml(t("cancel"))}</button>` +
        `<button type="button" class="btn btn-sm ${danger ? "btn-danger" : "btn-accent"}" data-rr="ok">${escapeHtml(libelle)}</button>` +
      `</div>`;
    ancre.insertAdjacentElement("afterend", note);
    if(geste) geste.setAttribute("aria-expanded", "true");
    const bAnnuler = note.querySelector('[data-rr="annuler"]');
    const bOk = note.querySelector('[data-rr="ok"]');
    const err = note.querySelector(".rr-confirm-err");
    let enCours = false;   // vrai du clic sur le bouton d'action jusqu'à l'issue de `action()`
    // `issue` : vrai quand c'est l'issue de l'action qui ferme ; tant que l'action court, rien d'autre ne ferme la note.
    const fermer = (ok, issue)=>{
      if(enCours && !issue) return;
      note.remove();
      if(geste) geste.removeAttribute("aria-expanded");
      if(rrConfirmCourante === fermer) rrConfirmCourante = null;
      // Fermée sans confirmer : le focus revient au geste ; une note confirmée ne le déplace pas (la relecture refait l'écran).
      if(!ok && geste && geste.isConnected) geste.focus();
      resolve(ok);
    };
    Object.defineProperty(fermer, "enCours", {get: ()=> enCours});
    rrConfirmCourante = fermer;
    bAnnuler.addEventListener("click", ()=> fermer(false));
    note.addEventListener("keydown", (e)=>{
      if(e.key === "Escape"){ e.stopPropagation(); fermer(false); }
    });
    bOk.addEventListener("click", async ()=>{
      if(enCours) return;
      enCours = true;
      bAnnuler.disabled = true; bOk.disabled = true;
      err.hidden = true;
      try {
        await action();
        enCours = false;
        fermer(true, true);
      } catch(e){
        enCours = false;
        err.textContent = (e && e.message) || t("error_generic");
        err.hidden = false;
        bAnnuler.disabled = false; bOk.disabled = false;
      }
    });
    (danger ? bAnnuler : bOk).focus();
  });
}

/* ---------- Toast ---------- */
let toastTimer=null;
function showToast(msg, genre){
  if(inviteGarde) return; // Lot « L'accès invité » (R11) : pas de second message du geste refusé
  const el = $("#toast");
  el.textContent = msg;
  // Lot « La charte commune de l'App » (v1.0079) : une erreur reste jusqu'à ce qu'on la touche ; la réussite s'efface.
  el.classList.toggle("erreur", genre === "erreur");
  el.classList.add("show");
  clearTimeout(toastTimer);
  if(genre !== "erreur") toastTimer = setTimeout(()=> el.classList.remove("show"), 1800);
}

/* ---------- Nav app ---------- */
async function switchAppView(view){
  currentAppView = view;
  $("#screen-app").dataset.view = view;   // Lot « La Planification en grand écran » (v1.0077) : la CSS du grand écran lit la vue
  $$(".topbar-nav button").forEach(b=> b.classList.toggle("active", b.dataset.view===view));
  syncTopbarNavScroll();
  $("#view-planche").classList.toggle("hidden", view!=="planche");
  $("#view-hebdo").classList.toggle("hidden", view!=="hebdo");
  if(view === "hebdo"){
    // Lot 4 §4 : ne jamais réafficher un tableau hebdo périmé depuis le
    // cache — un invalidate reçu pendant qu'on était sur la Planche marque
    // `hebdoStale`, et on refetch ici plutôt qu'au prochain reload manuel.
    if(hebdoStale || !hebdoData){
      await refreshHebdo();
    } else {
      renderHebdo();
    }
  }
}

/* ================= Lot D2③ : écran Missions ================= */

// Lot 3.4 §5 : extrait en constante partagée -- l'écran Campagnes en a
// besoin pour peupler son sélecteur (`campaignSimOptionsHtml()` plus
// bas), sans inventer une quatrième liste de simulateurs. `simLabel()`
// garde exactement son contrat d'avant (repli générique pour tout `sim`
// inconnu, §11.1).
const KNOWN_SIMS = { dcs:"DCS World", il2gb:"IL-2 GB", il2k:"IL-2 Korea" };

function simLabel(code){
  return KNOWN_SIMS[code] || (code||"").toUpperCase();
}

// Options du sélecteur Simulateur de l'écran Campagnes (Lot 3.4, §3/§5) --
// TOUS les simulateurs connus, jamais seulement ceux déjà présents dans
// les missions chargées (à la différence de `missionsDistinctSims()`,
// impropre ici : une campagne doit pouvoir se créer pour un simulateur
// qui n'a encore aucune mission déposée).
function campaignSimOptionsHtml(selected){
  return Object.entries(KNOWN_SIMS)
    .map(([code,label])=>`<option value="${escapeHtml(code)}"${code===selected?" selected":""}>${escapeHtml(label)}</option>`)
    .join("");
}


function fmtSessionDate(dateStr){
  if(!dateStr) return {d:"—", m:""};
  const [y,m,d] = dateStr.split("-").map(Number);
  return {d:String(d).padStart(2,"0"), m: MONTHS_ABBR[currentLang][m-1]};
}
function fmtSessionDateInline(dateStr){
  if(!dateStr) return "—";
  const [y,m,d] = dateStr.split("-").map(Number);
  return `${String(d).padStart(2,"0")}/${String(m).padStart(2,"0")}`;
}

function missionsMonthKey(dateStr){
  if(!dateStr) return null;
  const [y,m] = dateStr.split("-").map(Number);
  return `${y}-${String(m).padStart(2,"0")}`;
}
function missionsMonthLabel(key){
  const [y,m] = key.split("-").map(Number);
  return `${MONTHS[currentLang][m-1]} ${y}`;
}

function missionsDistinctSims(){
  return Array.from(new Set((DEBRIEF_SESSIONS||[]).map(s=> s.sim))).sort();
}
function missionsDistinctSquadrons(){
  const set = new Set();
  (DEBRIEF_SESSIONS||[]).forEach(s=> (s.squadrons||[]).forEach(sq=> set.add(sq)));
  return Array.from(set).sort();
}
function missionsDistinctYears(){
  const set = new Set();
  (DEBRIEF_SESSIONS||[]).forEach(s=>{ if(s.mission_date) set.add(s.mission_date.slice(0,4)); });
  return Array.from(set).sort().reverse();
}

// Lot « Déposer depuis la barre du haut » : les mois de l'année choisie qui ont une mission (du jeu choisi), du plus
// récent au plus ancien, comme les années ; aucun sans année choisie.
function missionsDistinctMonths(){
  if(missionsFilters.year === "all") return [];
  const set = new Set();
  (DEBRIEF_SESSIONS||[]).forEach(s=>{
    if(missionsFilters.sim && s.sim !== missionsFilters.sim) return;
    if(s.mission_date && s.mission_date.slice(0,4) === missionsFilters.year) set.add(s.mission_date.slice(5,7));
  });
  return Array.from(set).sort().reverse();
}

function missionsFiltered(){
  return (DEBRIEF_SESSIONS||[]).filter(s=>{
    if(missionsFilters.sim && s.sim !== missionsFilters.sim) return false;
    if(missionsFilters.squadron !== "all" && !(s.squadrons||[]).includes(missionsFilters.squadron)) return false;
    if(missionsFilters.year !== "all" && (!s.mission_date || s.mission_date.slice(0,4) !== missionsFilters.year)) return false;
    if(missionsFilters.month !== "all" && (!s.mission_date || s.mission_date.slice(5,7) !== missionsFilters.month)) return false;
    return true;
  });
}

function missionsGrouped(list){
  const groups = new Map();
  const noDate = [];
  list.forEach(s=>{
    const key = missionsMonthKey(s.mission_date);
    if(key===null){ noDate.push(s); return; }
    if(!groups.has(key)) groups.set(key, []);
    groups.get(key).push(s);
  });
  const sortedKeys = Array.from(groups.keys()).sort().reverse(); // antéchronologique
  const result = sortedKeys.map(k=> ({
    label: missionsMonthLabel(k),
    items: groups.get(k).slice().sort((a,b)=> (b.mission_date||"").localeCompare(a.mission_date||"")),
  }));
  if(noDate.length) result.push({ label: t("missions_no_date"), items: noDate });
  return result;
}

async function ensureMissionsLoaded(){
  if(missionsLoadState === "ready" || missionsLoadState === "loading"){ renderMissions(); return; }
  await loadMissions();
}

// Lot 2.3 §4.8 : chargée une fois, réutilisée par la modale Déposer et le
// panneau d'édition de session -- même patron paresseux que PROFILES pour
// le sélecteur de déposant. Échec silencieux (liste vide) : le sélecteur
// reste utilisable (option "Aucune" seule), jamais bloquant.
// Correctif Lot 3.4 §5 : `GET /api/debrief/campaigns` filtre par
// simulateur, `dcs` par défaut côté serveur -- cet appel ne passait
// jusqu'ici AUCUN paramètre, rendant toute campagne d'un autre simulateur
// invisible dans les deux sélecteurs (dépôt, édition de session). `sim`
// est désormais transmis par l'appelant : le sim de la session en édition
// (connu), `dcs` au dépôt (aucun sim n'est encore connu à ce stade -- le
// dépôt ne demande pas de simulateur, il se déduit du fichier après
// upload -- valeur assumée, seul geste de ce lot sur le module Débrief).
async function ensureCampaignsLoaded(sim){
  if(DEBRIEF_CAMPAIGNS !== null) return;
  try {
    const data = await apiFetch("/api/debrief/campaigns?sim=" + encodeURIComponent(sim || "dcs"));
    DEBRIEF_CAMPAIGNS = data.campaigns || [];
  } catch(e){
    DEBRIEF_CAMPAIGNS = [];
  }
}

// `selectedId` : id de campagne courant (chaîne vide si aucune) -- première
// option toujours vide (§4.8a/b, "vaut détacher").
function campaignOptionsHtml(selectedId){
  const opts = [`<option value="">${escapeHtml(t("campaign_none_option"))}</option>`];
  (DEBRIEF_CAMPAIGNS||[]).forEach(c=>{
    opts.push(`<option value="${escapeHtml(c.id)}" ${c.id===selectedId?"selected":""}>${escapeHtml(c.name)}</option>`);
  });
  return opts.join("");
}

/* Lot « Mission ou training » : le tampon d'un training et les options de la nature. */
// Le tampon d'un training : la famille du tampon PERSONNEL du Dossier (double cadre, encre usée, posé de biais),
// à l'encre bleue d'exercice ; l'inclinaison se tire sur l'identifiant de la session, stable d'un écran à l'autre.
function natureStampHtml(s){
  if(!s || s.nature !== "training") return "";
  const h = decorumSeed(`${String(s.id)}|nature`);
  const rot = -4 - ((h >>> 11) % 5);
  const mot = t("nature_stamp"), sous = t("nature_stamp_sub");
  return `<span class="nature-tampon" style="--rot:${rot}deg"><svg viewBox="0 0 150 58" role="img" aria-label="${escapeAttr(mot)}">
      <g filter="url(#nature-usure)" fill="none" stroke="currentColor">
        <rect x="2" y="2" width="146" height="54" rx="6" stroke-width="3"/><rect x="7.5" y="7.5" width="135" height="43" rx="3" stroke-width="1.1"/>
        <text x="75" y="31" text-anchor="middle" font-size="20" font-weight="700" fill="currentColor" stroke="none" textLength="112" lengthAdjust="spacingAndGlyphs" style="font-family:var(--font-label)">${escapeHtml(mot.toUpperCase())}</text>
        <path d="M22 37.5h106" stroke-width="1" stroke-dasharray="2 2.5"/>
        <text x="75" y="48" text-anchor="middle" font-size="10" font-weight="700" letter-spacing=".8" fill="currentColor" stroke="none" textLength="104" lengthAdjust="spacingAndGlyphs" style="font-family:var(--font-label)">${escapeHtml(sous)}</text>
      </g></svg></span>`;
}
function natureOptionsHtml(cur){
  return ["mission","training"].map(n => `<option value="${n}"${n===cur?" selected":""}>${escapeHtml(t("nature_"+n))}</option>`).join("");
}

async function loadMissions(){
  missionsLoadState = "loading";
  missionsError = null;
  renderMissions();
  try {
    const data = await apiFetch("/api/debrief/sessions");
    DEBRIEF_SESSIONS = data.sessions || [];
    missionsLoadState = "ready";
  } catch(e){
    missionsLoadState = "error";
    missionsError = e.message || t("error_generic");
  }
  renderMissions();
}

function missionsToolbarHtml(sims, squadrons, years){
  const simOptions = sims.map(s=>
    `<option value="${escapeHtml(s)}" ${s===missionsFilters.sim?"selected":""}>${escapeHtml(simLabel(s))}</option>`
  ).join("");
  const squadronChips = [`<span class="chip ${missionsFilters.squadron==="all"?"on":""}" data-chip-group="squadron" data-chip="all">${escapeHtml(t("chip_all_squadrons"))}</span>`]
    .concat(squadrons.map(sq=> `<span class="chip ${missionsFilters.squadron===sq?"on":""}" data-chip-group="squadron" data-chip="${escapeHtml(sq)}">${escapeHtml(sq)}</span>`))
    .join("");
  const yearChips = years.map(y=> `<span class="chip ${missionsFilters.year===y?"on":""}" data-chip-group="year" data-chip="${escapeHtml(y)}">${escapeHtml(y)}</span>`)
    .concat([`<span class="chip ${missionsFilters.year==="all"?"on":""}" data-chip-group="year" data-chip="all">${escapeHtml(t("chip_all_years"))}</span>`])
    .join("");
  // Lot « Déposer depuis la barre du haut » : une seconde ligne, les mois de l'année choisie, seulement quand une année l'est.
  const months = missionsDistinctMonths();
  const monthRow = months.length ? `<div class="tbar">${months.map(m=> `<span class="chip ${missionsFilters.month===m?"on":""}" data-chip-group="month" data-chip="${m}">${escapeHtml(MONTHS[currentLang][Number(m)-1])}</span>`)
    .concat([`<span class="chip ${missionsFilters.month==="all"?"on":""}" data-chip-group="month" data-chip="all">${escapeHtml(t("chip_all_months"))}</span>`])
    .join("")}</div>` : "";
  return `<div class="tbar">
    <span class="chip simsw"><select id="sim-select">${simOptions}</select></span>
    ${squadronChips}
    ${yearChips}
  </div>${monthRow}`;
}

function namedSampleHtml(s){
  // Lot D2④ Volet B : noms tronqués (named_sample, au plus 4) + overflow
  // "+K" si n_named dépasse l'échantillon renvoyé par l'API.
  // Lot 1.4b : ne retourne plus de <span> à part -- fragment de texte
  // consommé par la chaîne agrégée de .mt (§5.3/§5.4 du brief).
  const sample = s.named_sample || [];
  if(sample.length === 0) return "";
  const overflow = (s.n_named||0) - sample.length;
  let txt = sample.map(n=> escapeHtml(n)).join(", ");
  if(overflow > 0) txt += ` +${overflow}`;
  return txt;
}

function sessionCardHtml(s){
  const dt = fmtSessionDate(s.mission_date);
  const acmiOn = !!s.acmi_present;
  const pct = s.doc_ratio==null ? null : Math.round(s.doc_ratio*100);
  const squadronsHtml = (s.squadrons||[]).map(sq=> `<span class="pill">${escapeHtml(sq)}</span>`).join("");
  // Révision ④.1 chgt 4 : bouton de suppression discret, admin uniquement
  // (ME chargé avant tout rendu -- cf. init()/loadMe()). Jamais de
  // suppression sans confirmation (câblée dans wireMissionsMount).
  // Lot « Le Débrief : quatre défauts » : la garde est `is_admin`, comme
  // « Recalc. » et la route DELETE côté serveur (403 sinon).
  const deleteBtn = (ME && ME.is_admin === true)
    ? `<button type="button" class="btn btn-ghost btn-icon btn-sm sc-delete-btn" data-delete-session="${escapeHtml(s.id)}" title="${escapeHtml(t("debrief_delete_session_title"))}" aria-label="${escapeHtml(t("debrief_delete_session_title"))}">${SVG_ICON_TRASH}</button>`
    : "";
  // Lot 1.4b §5.4 (arbitrage cadrage §5.1, option C) : les 4 <span> à icône
  // SVG + le badge d'effectif fusionnent en une chaîne unique séparée par
  // " · ", ordre imposé vols/pilotes/kills/durée/anonymes puis échantillon
  // de noms. Segment omis si la donnée est nulle ou absente -- jamais de
  // " ·  · ". Aucune icône SVG ne subsiste dans .sx.
  // Lot Jauge ② v0.9928 (brief §7.3) : le segment "membres" (n_pilots)
  // disparaît -- il affichait la même valeur que "pilotes" sur toutes les
  // sessions observées. Remplacé par "anonymes" (n_anon). `n_pilots` reste
  // servi par l'API (les escadrilles en dépendent), simplement plus lu ici.
  const sample = namedSampleHtml(s);
  const mtParts = [
    (s.n_flights!=null) ? `${s.n_flights} ${escapeHtml(t("meta_flights"))}` : null,
    (s.n_named!=null) ? `${s.n_named} ${escapeHtml(t("meta_pilots"))}` : null,
    (s.n_kills!=null) ? `${s.n_kills} ${escapeHtml(t("meta_kills"))}` : null,
    (s.duration_s!=null) ? escapeHtml(fmtDuree(s.duration_s)) : null,
    (s.n_anon!=null) ? `${s.n_anon} ${escapeHtml(t("meta_anon"))}` : null,
    sample || null,
  ].filter(p=> p);
  const mtHtml = mtParts.join(" · ");
  // Lot 2.3 §4.8c/§5 : pastille typographique générique (`.camp`, jamais
  // renommée -- trois autres écrans futurs la réutilisent). Émise entre
  // ${mtHtml} et ${squadronsHtml}, ordre de la maquette (body_missions.
  // html:36). Omise si la session n'a pas de campagne.
  // Lot « L'écran C » : la pastille ouvre la fiche de la campagne, et seulement elle
  // (wireMissionsMount ignore un clic venu d'un [data-ouvre-campagne]).
  const campHtml = s.campaign ? `<a class="camp ink" href="#" data-ouvre-campagne="${escapeAttr(String(s.campaign.id))}">${escapeHtml(s.campaign.name)}</a>` : "";
  // Lot 1.5 §3 — tampon "Incomplet" sur la carte Missions, UNIQUEMENT si
  // aucun vol de la session n'est détaillé (jauge à 0 sur N) : session
  // entièrement rebâtie depuis l'ACMI, rare. Jamais posé sur la session
  // elle-même via un binaire dans les autres cas (§3 du brief) -- la jauge
  // .dm ci-dessous reste seule à qualifier une session partiellement documentée.
  const stampHtml = (pct === 0 && s.n_flights > 0)
    ? `<span class="stamp ink worn">${escapeHtml(t("flight_stamp_incomplete"))}</span>` : "";
  // Lot Fraîcheur v0.9939 (brief §8 F1) : marque sourde distincte du tampon
  // rouge ci-dessus -- une pochette peut porter les deux à la fois (cas
  // réel de la fixture). Trait pointillé en encre sourde contre trait plein
  // en encre rouge : les deux doivent rester visuellement distincts.
  const perimeHtml = s.stats_stale
    ? `<span class="perime">${escapeHtml(t("stale_mark"))}</span>` : "";
  return `<div class="scard" data-open-session="${escapeHtml(s.id)}" tabindex="0" role="button">
    <div class="sd">${dt.d}<small>${escapeHtml(dt.m)}</small>${natureStampHtml(s)}</div>
    <div class="sm">
      <div class="st2">${escapeHtml(s.display_title)}${stampHtml}${perimeHtml}${verifMarkHtml(s)}</div>
      <div class="sx">
        <span class="mt">${mtHtml}</span>
        ${campHtml}
        ${squadronsHtml}
      </div>
    </div>
    <div class="ss">
      ${deleteBtn}
      <span class="pill ${acmiOn?"":"off"}">${escapeHtml(acmiOn?t("acmi_on"):t("acmi_off"))}</span>
      <div class="dm">
        <span class="mg"><i style="width:${pct==null?0:pct}%"></i></span>
        <span class="dp">${pct==null?"—":pct+" % "+escapeHtml(t("doc_label"))}</span>
      </div>
    </div>
  </div>`;
}

// Lot « Le rattachement des dépôts » (v1.0052) : la marque « À vérifier » -- la classe de « à recalculer »
// (`.perime`), aucune règle neuve ; posée après elle, sur la carte de Missions et dans l'en-tête de la Session.
function verifMarkHtml(s){
  return (s && s.a_verifier)
    ? `<span class="perime" title="${escapeAttr(t("verif_mark_title"))}">${escapeHtml(t("verif_mark"))}</span>` : "";
}

// Lot « La charte commune, au Débrief » (v1.0080) : la note commune sous le geste (`rrConfirmer`) remplace la boîte grise
// du navigateur ; elle dit ce qui disparaît (vols et fichiers déposés de la session) et garde le refus du serveur
// (403, 409 rédaction en cours) sans se fermer.
async function deleteDebriefSession(id, btn){
  if(estInviteEcran()){ showToast(t("invite_lecture_seule")); return; } // lot « L'accès invité » (R11)
  const s = (DEBRIEF_SESSIONS||[]).find(x=> String(x.id) === String(id)) || {};
  const nv = s.n_flights||0, nd = s.n_uploads||0;
  const pluriel = (n)=> n > 1 ? "s" : "";
  const texte = escapeHtml(t("debrief_suppr_texte")
    .split("{nv}").join(String(nv)).split("{sv}").join(pluriel(nv))
    .split("{nd}").join(String(nd)).split("{sd}").join(pluriel(nd))
    .split("{titre}").join(s.display_title||""));   // le titre en dernier : un jeton qu'il contiendrait reste tel quel
  const ok = await rrConfirmer({
    ancre: btn.closest("[data-open-session]"), geste: btn,
    titre: t("debrief_suppr_titre"), texte, libelle: t("delete"), danger: true,
    action: async ()=>{
      let res;
      try { res = await fetch(`/api/debrief/sessions/${id}`, {method:"DELETE", credentials:"same-origin"}); }
      catch(e){ throw new Error(t("error_generic")); }
      if(res.status === 403) throw new Error(t("debrief_delete_forbidden"));
      if(res.status === 409) throw new Error(t("debrief_delete_redaction")); // lot « Finitions du Débrief » (ARC-29)
      if(!res.ok) throw new Error(t("error_generic"));
    }
  });
  if(!ok) return;
  showToast(t("debrief_toast_session_deleted"));
  await loadMissions(); // retire la carte + rafraîchit la liste (chgt 4)
}

// Lot 1.5 §2.1 — squelette de chargement de l'écran Missions. Le cartouche
// (déjà dans le gabarit statique de #view-missions, jamais touché ici) reste
// affiché tel quel ; ce squelette ne porte que le contenu du mount : l'entête
// est un intitulé i18n connu avant la donnée -- rendu pour de vrai -- puis
// des .bar en lieu et place de la barre d'outils et des pochettes de session.
function missionsSkeletonHtml(){
  const cardBar = `<div class="scard" style="pointer-events:none">
    <div class="sd"><span class="bar" style="width:1.8rem;height:1.4rem"></span></div>
    <div class="sm">
      <div class="st2"><span class="bar" style="width:60%"></span></div>
      <div class="sx"><span class="bar" style="width:40%"></span></div>
    </div>
    <div class="ss"><span class="bar" style="width:4rem"></span></div>
  </div>`;
  return `<div class="tbar"><span class="bar" style="width:8rem"></span></div>`
    + cardBar + cardBar + cardBar;
}

function renderMissions(){
  const mount = $("#missions-mount");
  if(!mount) return;

  if(missionsLoadState === "loading" && !DEBRIEF_SESSIONS){
    mount.innerHTML = missionsSkeletonHtml();
    return;
  }
  if(missionsLoadState === "error"){
    mount.innerHTML = `<div class="state fail">
      <p>${escapeHtml(missionsError || t("error_generic"))}</p>
      <button type="button" class="btn btn-sm" data-missions-retry>${escapeHtml(t("retry"))}</button>
    </div>`;
    return;
  }
  if(!DEBRIEF_SESSIONS){
    mount.innerHTML = missionsSkeletonHtml();
    return;
  }
  if(DEBRIEF_SESSIONS.length === 0){
    mount.innerHTML = `<div class="state void">
      <p>${escapeHtml(t("missions_empty"))}</p>
      <button type="button" class="btn btn-primary" data-open-deposer>${escapeHtml(t("deposer"))}</button>
    </div>`;
    return;
  }

  const sims = missionsDistinctSims();
  if(!missionsFilters.sim || !sims.includes(missionsFilters.sim)) missionsFilters.sim = sims[0];
  const squadrons = missionsDistinctSquadrons();
  const years = missionsDistinctYears();

  const filtered = missionsFiltered();
  const groups = missionsGrouped(filtered);

  // Lot 1.4b §5.5 : le bouton CTA quitte l'entête et entre dans la barre
  // d'outils fondue (dernier enfant, margin-left:auto porté par la
  // maquette -- plus de conteneur spaceur dédié).
  // Lot 1.5b §9 : l'entête générique (page-head/h1) est éteinte ; le titre
  // vit désormais dans la cartouche statique (index.html, §11).
  let html = missionsToolbarHtml(sims, squadrons, years);
  if(groups.length === 0){
    html += `<div class="state void"><p>${escapeHtml(t("missions_no_match"))}</p></div>`;
  } else {
    groups.forEach(g=>{
      // Lot 1.4b : vocabulaire de groupe de mois fondu en trois enfants
      // (libellé / filet / décompte) -- les pochettes sont enfants directs
      // du mount, comme dans la maquette (§5.5), plus de conteneur de liste
      // dédié.
      html += `<div class="mgroup">
        <span class="ml">${escapeHtml(g.label)}</span><span class="mr"></span><span class="mc">${g.items.length} ${escapeHtml(t("missions_word"))}${g.items.length>1?"s":""}</span>
      </div>`;
      html += g.items.map(sessionCardHtml).join("");
    });
  }
  mount.innerHTML = html;
}

function openSession(id){
  goDebrief("session", {sessionId:id});
}

/* ================= Lot D2④ : écran Session (contenu réel) ================= */

async function ensureSessionLoaded(id){
  if(!id) return;
  if(CURRENT_SESSION && CURRENT_SESSION.id === id && sessionDetailLoadState === "ready"){
    renderSession();
    return;
  }
  // Chgt 1 : l'état de dépli des groupes roster est propre à une session --
  // repartir propre en changeant de session (clés potentiellement homonymes
  // d'une session à l'autre, ex. même pilote).
  rosterExpandedGroups = new Set();
  // Lot 2.1 §4.8b : idem pour le bloc d'édition nom/note.
  sessionEditOpen = false;
  // Lot « Le rattachement des dépôts » : idem pour le déplacement et la fusion.
  sessionMoveUploadId = null;
  sessionMergeChoice = "";
  sessionMergeConfirm = false;
  sessionDetailLoadState = "loading";
  sessionDetailError = null;
  renderSession();
  try {
    CURRENT_SESSION = await apiFetch(`/api/debrief/sessions/${id}`);
    sessionDetailLoadState = "ready";
    rrChargeFaite("session", id);   // lot « Le retour et l'adresse »
  } catch(e){
    sessionDetailLoadState = "error";
    sessionDetailError = e.message || t("error_generic");
    if(rrChargeRefusee("session", id, e)) return;   // ouverte par l'adresse : une 4xx ramène à Missions
  }
  renderSession();
}

// Lot 1.4d — squelette de chargement de l'écran Session, vocabulaire DA.
// Les quatre panneaux et leurs intitulés (constantes i18n, connus avant la
// donnée) se dessinent pour de vrai ; seules les zones de donnée portent
// des .bar -- la barre de squelette du catalogue, sans collision possible
// puisque la piste de la jauge est ailleurs renommée .gt (§5.1).
function sessionSkeletonHtml(){
  const panel = (titleKey, rows)=> `<div class="framed">
    <div class="sec ink">${escapeHtml(t(titleKey))}</div>
    ${rows}
  </div>`;
  return `<div class="idbar"><div><div class="kick"><span class="bar" style="width:8rem;height:.9rem"></span></div><div class="callsign ink worn"><span class="bar" style="width:14rem;height:2rem"></span></div></div></div><div class="rule2 ink"></div>`
    + panel("session_doc_title", `<span class="bar" style="width:100%;height:1.4rem"></span>`)
    + panel("session_roster_title", `<span class="bar" style="width:100%"></span><span class="bar" style="width:100%;margin-top:.4rem"></span><span class="bar" style="width:100%;margin-top:.4rem"></span>`)
    + `<div class="duo">`
    + panel("session_graveyard_title", `<span class="bar" style="width:100%"></span>`)
    + panel("session_facts_title", `<span class="bar" style="width:100%"></span>`)
    + `</div>`;
}

function renderSession(){
  // Lot 1.4d §6.1 : référence verticale, recalculée à chaque rendu (même
  // discipline que Vol, 1.5b §12).
  updateSessionMref();

  const mount = $("#session-mount");
  if(!mount) return;

  if(sessionDetailLoadState === "loading" && !(CURRENT_SESSION && CURRENT_SESSION.id===CURRENT_SESSION_ID)){
    mount.innerHTML = sessionSkeletonHtml();
    return;
  }
  if(sessionDetailLoadState === "error"){
    mount.innerHTML = `<div class="state fail">
      <p>${escapeHtml(sessionDetailError || t("error_generic"))}</p>
      <button type="button" class="btn btn-sm" data-session-retry>${escapeHtml(t("session_error_retry"))}</button>
    </div>`;
    return;
  }
  if(!CURRENT_SESSION || CURRENT_SESSION.id !== CURRENT_SESSION_ID){
    mount.innerHTML = sessionSkeletonHtml();
    return;
  }

  mount.innerHTML = sessionViewHtml(CURRENT_SESSION);
}

/* ---------- Helpers de données (calculs client, dérivés du contrat GET /sessions/{id}) ---------- */

function normCallsignJs(s){
  // Même règle simple que `engine._norm_callsign` côté moteur (brief Volet A
  // /ⓒ.3) : `|` -> espace, espaces multiples collapsés, minuscule. Ne peut
  // pas importer le Python depuis le front -- réimplémentation minimale et
  // volontairement alignée, jamais divergente.
  if(!s) return null;
  let x = s.replace(/\|/g, " ");
  x = x.replace(/\s+/g, " ").trim().toLowerCase();
  return x || null;
}

// Correctif « Le nom du membre » v1.0021 (R4) : le nom d'un vol est son
// indicatif observé ; à défaut, le nom du membre rattaché (`pilote_nom`, servi
// par l'API, nom de l'annuaire). Une seule fonction pour tout ce qui nomme ou
// groupe un vol -- la condition `identity_state === "anonyme"` reste devant,
// chez chaque appelant. Le bordereau (« Corriger », nom vu) lit toujours
// `pilot_callsign` : il parle de l'indicatif OBSERVÉ.
function flightName(f){
  return (f && (f.pilot_callsign || f.pilote_nom)) || "";
}

function shortCallsign(raw){
  // Règle de segment identique à `_extract_name_segment()` côté moteur
  // (`engine.py`, brief §2/§3 v0.9916) -- un commentaire y renvoie ici, et
  // réciproquement ; toute évolution de l'une doit être répercutée sur
  // l'autre. Coupe sur le DERNIER séparateur -- '|' ou 'I' majuscule isolé,
  // entouré d'espaces des deux côtés -- et garde ce qui suit ; repli sur la
  // chaîne entière si aucun séparateur (ex. "Night Owl" reste intact : son
  // 'i' interne n'est jamais isolé par des espaces).
  if(!raw) return "";
  const sepRe = /\s(\||I)\s/g;
  let lastMatch = null, m;
  while((m = sepRe.exec(raw)) !== null){
    lastMatch = m;
  }
  const segment = lastMatch ? raw.slice(lastMatch.index + lastMatch[0].length) : raw;
  return segment.trim();
}

function anonFlightLabel(ac){
  return currentLang==="fr" ? `Vol ${libType(ac)} anonyme` : `Anonymous ${libType(ac)} flight`;
}

function fmtDuree(s){
  // Lot « Durée » v0.9996, corrigé au v0.9997 : écriture unique de TOUTES les
  // durées de l'application -- roster, cartes Missions, en-tête de session,
  // carte du vol -- et, préfixée par "t+", des durées écoulées du module
  // Débrief. "48 min" sous l'heure, "1h05" au-delà, "1h" pile. Jamais de
  // secondes, et l'heure se colle : en fonte à chasse fixe, « 1 h 05 » se lit
  // comme trois valeurs séparées (jugé à l'écran par le porteur, 18 septembre).
  // Même écriture dans les deux langues. Remplaçait déjà fmtElapsed ("m:ss"
  // en deçà d'une heure, "h:mm" au-delà) et fmtDurationShort.
  if(s==null) return "—";
  const total = Math.max(0, Math.round(s));
  const h = Math.floor(total/3600);
  const m = Math.floor((total%3600)/60);
  if(h === 0) return `${m} min`;
  return m === 0 ? `${h}h` : `${h}h${String(m).padStart(2,"0")}`;
}

function fmtSessionDateFull(dateStr){
  if(!dateStr) return "—";
  const [y,m,d] = dateStr.split("-").map(Number);
  return `${String(d).padStart(2,"0")} ${MONTHS[currentLang][m-1]} ${y}`;
}

function depositorLabel(profileId){
  if(!profileId) return "—";
  const key = String(profileId);
  if(ME && key === String(ME.id)) return callsign(ME.name);
  const p = PROFILES.get(key);
  return p ? callsign(p.name) : "—";
}

/* ---------- Roster GROUPÉ PAR PILOTE (Révision ④.1 chgt 1) ----------
   §1.10 rappel : aucune compétition inter-membres -- le regroupement est
   une lecture descriptive, jamais un classement (jamais trié par kills). */

// État d'expansion des groupes -- survit aux re-rendus (renderSession() est
// rappelé après chaque clic de dépli), remis à zéro au changement de
// session (cf. ensureSessionLoaded).
let rosterExpandedGroups = new Set();

function flightDurationS(f){
  return (f.stats && f.stats.flight_time_s!=null) ? f.stats.flight_time_s
    : ((f.t_start!=null && f.t_end!=null) ? (f.t_end - f.t_start) : null);
}

function groupFlightsByPilot(flights){
  // Clé : vol nommé ou rattachable qui porte un nom (l'indicatif, sinon le
  // nom du membre -- flightName) -> ce nom normalisé (fusionne les respawns
  // d'un même pilote) ; vol anonyme, ou sans nom exploitable (garde-fou) ->
  // son propre object_id/acmi_track_id, un groupe par vie (jamais fusionné).
  const groups = new Map();
  flights.forEach(f=>{
    let key = null, kind = "named";
    if(f.identity_state !== "anonyme" && flightName(f)){
      const norm = normCallsignJs(flightName(f));
      if(norm) key = "cs:"+norm;
    }
    if(!key){
      key = "anon:" + (f.object_id || f.acmi_track_id || f.id);
      kind = "anon";
    }
    if(!groups.has(key)) groups.set(key, {key, kind, flights:[]});
    groups.get(key).flights.push(f);
  });
  // Les `flights` arrivent déjà triés par t_start (API) : l'ordre d'insertion
  // du Map ci-dessus correspond donc à l'ordre du t_start du 1ᵉʳ vol de
  // chaque groupe -- exactement l'ordre non compétitif demandé (§C.3),
  // aucun tri supplémentaire nécessaire (jamais par kills).
  return Array.from(groups.values());
}

function bestIdentityFlight(flights){
  // Meilleur état d'identité du groupe (nomme > rattachable > anonyme),
  // à égalité le vol le plus ancien (déjà en tête, ordre t_start).
  const rank = {nomme:0, rattachable:1, anonyme:2};
  return flights.reduce((best,f)=>
    (rank[f.identity_state]??3) < (rank[best.identity_state]??3) ? f : best, flights[0]);
}

function groupCoalition(flights){
  // Coalition majoritaire du groupe ; égalité -> celle du 1ᵉʳ vol (déterministe).
  const counts = new Map();
  flights.forEach(f=>{
    const c = (f.coalition==="1"||f.coalition==="2") ? f.coalition : "unknown";
    counts.set(c, (counts.get(c)||0)+1);
  });
  let best=null, bestN=-1;
  counts.forEach((n,c)=>{ if(n>bestN){ bestN=n; best=c; } });
  let tiedCount = 0;
  counts.forEach((n)=>{ if(n===bestN) tiedCount++; });
  if(tiedCount>1){
    const firstC = (flights[0].coalition==="1"||flights[0].coalition==="2") ? flights[0].coalition : "unknown";
    if(counts.get(firstC)===bestN) best = firstC;
  }
  return best==="unknown" ? null : best;
}

function respawnLabelText(n, nKia){
  if(n<=1) return currentLang==="fr" ? "1 vol" : "1 flight";
  if(nKia<=0) return currentLang==="fr" ? `${n} vols` : `${n} flights`;
  return currentLang==="fr"
    ? `${n} vols · ${nKia} respawn${nKia>1?"s":""} après KIA`
    : `${n} flights · ${nKia} respawn${nKia>1?"s":""} after KIA`;
}

function totalShots(stats){
  const sw = (stats && stats.shots_by_weapon) || {};
  let total = 0;
  Object.keys(sw).forEach(w=>{
    const v = sw[w] || {};
    total += (v.shots!=null ? v.shots : (v.releases!=null ? v.releases : 0));
  });
  return total;
}

function flightIssue(stats){
  if(!stats) return {key:"none", label:t("session_issue_none")};
  if(stats.crashed || stats.pilot_dead) return {key:"kia", label:t("session_issue_kia")};
  if(stats.ejected) return {key:"eject", label:t("session_issue_eject")};
  if((stats.landings||0) > 0) return {key:"rtb", label:t("session_issue_rtb")};
  return {key:"none", label:t("session_issue_none")};
}

const CATEGORY_ICON = {
  "Char":"target-char",
  "Défense AA":"target-aa",
  "Artillerie":"target-artillerie",
  "Blindé léger":"target-blinde-leger",
  "Infanterie":"target-infanterie",
  "Véhicule":"target-vehicule",
  "Navire":"target-navire",
  "Hélicoptère":"target-helicoptere",
  "Avion":"target-avion",
  "Static":"target-static",
  "Inconnu":"target-inconnu",
}; // NOTE Lot 1.4d : dernier appelant (sessionGraveyardPanelHtml, icônes
   // par catégorie) retiré -- la maquette du bilan (.bcat) n'a pas
   // d'icône par ligne. Conservée : aucun autre écran ne s'en sert
   // aujourd'hui mais elle documente le référentiel de catégories et son
   // repli "Inconnu" -> target-inconnu, réutilisable si un futur écran en
   // a besoin. Écart signalé en rapport, pas retirée par prudence (une
   // suppression est irréversible dans l'historique visuel, un objet de
   // données inerte ne l'est pas).

// Lot « La plume » §6 : la SEULE fonction qui rend le libellé d'une catégorie de
// cible dans la langue de l'écran. La valeur de la catégorie reste la donnée (API,
// base, CATEGORY_ICON, valeurs des <option>) ; une catégorie inconnue s'affiche
// telle quelle.
const CATEGORY_I18N_KEY = {
  "Avion":"cat_avion",
  "Hélicoptère":"cat_helicoptere",
  "Défense AA":"cat_defense_aa",
  "Char":"cat_char",
  "Artillerie":"cat_artillerie",
  "Blindé léger":"cat_blinde_leger",
  "Infanterie":"cat_infanterie",
  "Véhicule":"cat_vehicule",
  "Navire":"cat_navire",
  "Static":"cat_static",
  "Inconnu":"cat_inconnu",
};
function catLabel(cat){
  const key = CATEGORY_I18N_KEY[cat];
  return key ? t(key) : cat;
}

/* ---------- Rendu des panneaux ---------- */

// Lot 1.4d §6.1 — chassis idbar, aligné sur Missions/Vol (1.5b). .kick =
// date (relogée depuis l'ancienne .lede) ; .callsign = titre de la
// session (relogé depuis l'ancien h1). .meta porte les DONNÉES réelles
// que la maquette ne prévoit pas -- type de sim et CTA rapport -- même
// discipline que .idbar .meta sur l'écran Vol (flightMetaHtml, §1.5b) :
// relogées, ni supprimées ni inventées. Théâtre : omis (aucune donnée
// théâtre au contrat GET /sessions/{id}, pas de repli inventé) -- ligne
// secondaire de .meta donc absente, comme le veut la discipline "pas de
// repli inventé" déjà tenue pour .kick sur l'écran Vol.
//
// Correctif finitions §3 : le débord de .callsign (titre = nom de fichier
// .miz brut, sans espace, arbitrairement long) est traité au catalogue
// (#screen-app[data-module="debrief"] .callsign, overflow-wrap:anywhere),
// pas ici -- le style en ligne d'origine est retiré. Vol en bénéficie du
// même geste, sans rien changer à ses propres gabarits.
/* ---------- Lot « Les liens de la soirée » (v1.0107) : la session montre la soirée planifiée du même jour ----------
   Le jour de la session : la date de Paris de `reference_time` (R590), sinon `mission_date` ; ni l'un ni l'autre : rien
   n'est lu. Une lecture (`GET /api/events?from=<jour>&to=<jour>`) par session chargée : le résultat se tient par l'objet
   `CURRENT_SESSION` lu, donc se relit quand la session se recharge et jamais à un simple redessin. Un échec ou aucune
   occurrence : rien, sans message. */
const SOIREE_PLANIFIEE = new WeakMap();

function jourDeParis(iso){
  if(!iso) return null;
  const d = new Date(iso);
  if(isNaN(d.getTime())) return null;
  const p = {};
  new Intl.DateTimeFormat("en-CA", {timeZone:fuseauEscadre(), year:"numeric", month:"2-digit", day:"2-digit"})
    .formatToParts(d).forEach(x=>{ p[x.type] = x.value; });
  return `${p.year}-${p.month}-${p.day}`;
}
function soireePlanifieeDe(s){
  const jour = jourDeParis(s.reference_time) || s.mission_date || null;
  if(!jour) return [];
  let e = SOIREE_PLANIFIEE.get(s);
  if(!e){
    e = {occs:null};
    SOIREE_PLANIFIEE.set(s, e);
    apiFetch(`/api/events?from=${encodeURIComponent(jour)}&to=${encodeURIComponent(jour)}`).then(liste=>{
      e.occs = (Array.isArray(liste) ? liste : []).filter(o=> o.occ_date === jour)
        .sort((a, b)=> new Date(a.start_at_utc) - new Date(b.start_at_utc));
      if(e.occs.length && CURRENT_SESSION === s && CURRENT_SESSION_ID === s.id) soireeNoteMettre(s);
    }, ()=>{ e.occs = []; });
  }
  return e.occs || [];
}
// La réponse n'écrit que la note, jamais toute la session : le panneau « Modifier » ouvert et ce qui s'y tape restent intacts.
// La note termine l'en-tête : après le filet, le panneau d'édition et la note à l'escadre, qui sont ses frères directs.
function soireeNoteMettre(s){
  const mount = $("#session-mount");
  if(!mount || sessionDetailLoadState !== "ready" || !mount.querySelector(":scope > .idbar [data-open-report]")) return;
  const html = soireePlanifieeHtml(s);
  const ancienne = mount.querySelector(":scope > .soiree-note");
  if(ancienne){
    if(html) ancienne.outerHTML = html; else ancienne.remove();
    return;
  }
  if(!html) return;
  let fin = mount.querySelector(":scope > .rule2");
  if(!fin) return;
  while(fin.nextElementSibling && (fin.nextElementSibling.id === "session-edit-panel"
        || (fin.nextElementSibling.classList.contains("note") && !fin.nextElementSibling.classList.contains("soiree-note")))){
    fin = fin.nextElementSibling;
  }
  fin.insertAdjacentHTML("afterend", html);
}
function soireePlanifieeHtml(s){
  const occs = soireePlanifieeDe(s);
  if(!occs.length) return "";
  const liens = occs.map(o=>
    `<a href="${escapeAttr(rrAdresseEcran("planif", "fiche", {ev: o.event_id, date: o.occ_date}))}">${escapeHtml(o.title)}, ${escapeHtml(fmtLocalTime(o.start_at_utc))}</a>`
  ).join(" · ");
  return `<div class="note soiree-note"><b>${escapeHtml(t("soiree_planifiee"))}</b> ${liens}</div>`;
}

function sessionHeaderHtml(s){
  const flights = s.flights||[];
  // Lot Jauge ② v0.9928 (brief §7.2) -- `groupFlightsByPilot()` cesse de
  // servir de compteur ici (elle reste dans le fichier pour le Roster,
  // second appelant plus bas). Champs servis par l'API (§6.2).
  const statLine = `${escapeHtml(fmtDuree(s.duration_s))} · ${flights.length} ${escapeHtml(t("session_roster_flights_word"))} · ${s.n_named||0} ${escapeHtml(t("meta_pilots"))} · ${s.n_anon||0} ${escapeHtml(t("meta_anon"))}`;
  // Lot 2.1 §4.8b : affordance d'édition, seulement si can_edit (droit
  // jamais décidé côté client seul -- le serveur l'expose sur GET /sessions/{id}).
  const editBtnHtml = s.can_edit
    ? `<button type="button" class="btn btn-sm" data-toggle-session-edit>${escapeHtml(t("session_edit_cta"))}</button>`
    : "";
  // Réutilise la primitive .field (rebranchée #view-session, §4.10) --
  // même patron que #field-depositor/#field-mission-name de la modale
  // Déposer. Pas de modale neuve (§4.8b, interdit §5.4).
  const editPanelHtml = (s.can_edit && sessionEditOpen)
    ? `<div class="framed" id="session-edit-panel">
        <div class="field">
          <label>${escapeHtml(t("session_edit_name_label"))}</label>
          <input type="text" id="session-edit-name-input" maxlength="80" value="${escapeAttr(s.display_name||"")}">
        </div>
        <div class="field">
          <label>${escapeHtml(t("session_edit_note_label"))}</label>
          <textarea id="session-edit-note-input" maxlength="2000" rows="3">${escapeHtml(s.wing_note||"")}</textarea>
        </div>
        <div class="field">
          <label>${escapeHtml(t("session_edit_campaign_label"))}</label>
          <select id="session-edit-campaign-select" data-initial="${escapeAttr(s.campaign?s.campaign.id:"")}">${campaignOptionsHtml(s.campaign?s.campaign.id:"")}</select>
        </div>
        <div class="field">
          <label>${escapeHtml(t("nature_label"))}</label>
          <select id="session-edit-nature-select" data-initial="${escapeAttr(s.nature||"mission")}">${natureOptionsHtml(s.nature||"mission")}</select>
        </div>
        ${sessionMergeFieldHtml(s)}
        <div style="display:flex;gap:.5rem;justify-content:flex-end;margin-top:.6rem">
          <button type="button" class="btn btn-sm" data-cancel-session-edit>${escapeHtml(t("session_edit_cancel"))}</button>
          <button type="button" class="btn btn-sm btn-accent" data-save-session-edit>${escapeHtml(t("session_edit_save"))}</button>
        </div>
      </div>`
    : "";
  // Lot 2.1 §4.8c : si et seulement si non vide -- pas de bloc vide, pas de
  // libellé orphelin.
  const noteHtml = (s.wing_note && s.wing_note.trim())
    ? `<div class="note"><b>${escapeHtml(t("session_wing_note_label"))}</b> ${escapeHtml(s.wing_note)}</div>`
    : "";
  // Lot « Recalcul de session » v0.9914 -- admin uniquement (ME.is_admin
  // === true, strict, même garde que slipHtml, v0.9917), jamais une
  // capacité distribuable. Recalcul complet depuis les fichiers déposés.
  const recomputeBtnHtml = (ME && ME.is_admin === true)
    ? `<button type="button" class="btn btn-sm" data-recompute-session>${escapeHtml(t("recompute_cta"))}</button>`
    : "";
  // Lot Fraîcheur v0.9939 (brief §8 F2) : précédent de la DA -- l'écran Vol
  // fait déjà exactement ça, flightHeaderHtml() : `.callsign.ink.worn`
  // porte `.etat` en ligne après le nom. `.perime` en est le troisième
  // membre (avec `.stamp`), même géométrie, ne dévie d'aucune valeur.
  const perimeHtml = s.stats_stale
    ? `<span class="perime">${escapeHtml(t("stale_mark"))}</span>` : "";
  // Correctif v0.9940 (Addendum 3 §1/§2) : la tâche de fond ne s'exécute
  // qu'au démarrage -- en régime établi (plus de redémarrage), ce bouton
  // ne couvre plus que le cas où elle a échoué en silence ou n'a pas fini.
  // Sa présence devient donc une information en soi : il ne paraît que
  // lorsqu'il y a quelque chose à réparer (stale_count > 0), et son
  // libellé porte le compte -- patron de pluriel de la maison, comme
  // ${g.items.length} ${t("missions_word")}${g.items.length>1?"s":""} sur
  // l'écran Missions, ici assemblé via les jetons {n}/{s} de la chaîne.
  // Ne touche jamais au libellé `Recalc.` (recompute_cta) : il désigne
  // cette session précise, le compte suffit désormais à distinguer les
  // deux boutons.
  const staleCount = s.stale_count || 0;
  const recomputeAllBtnHtml = (ME && ME.is_admin === true && staleCount > 0)
    ? `<button type="button" class="btn btn-sm" data-recompute-all-stale>${escapeHtml(
        t("recompute_all_cta").replace("{n}", staleCount).replace("{s}", staleCount > 1 ? "s" : "")
      )}</button>`
    : "";
  return `<div class="idbar">
    <div>
      <div class="kick">${escapeHtml(fmtSessionDateFull(s.mission_date))}</div>
      <div class="callsign ink worn">${escapeHtml(s.display_title)}${perimeHtml}${verifMarkHtml(s)}</div>
    </div>
    <div class="meta"><b>${statLine}</b>
      <span class="sim-badge">${escapeHtml((s.sim||"").toUpperCase())}</span>
      <div class="idacts">
        ${natureStampHtml(s)}
        <button type="button" class="btn btn-sm" data-open-report>${escapeHtml(t("session_report_cta"))}</button>
        ${editBtnHtml}
        ${recomputeBtnHtml}
        ${recomputeAllBtnHtml}
      </div>
    </div>
  </div>
  <div class="rule2 ink"></div>${editPanelHtml}${noteHtml}${soireePlanifieeHtml(s)}`;
}

// Lot 1.4d §6.3/§6.4 — panneau Documentation, vocabulaire DA. .gauge
// (piste renommée .gt, §5.1). Le sous-bloc "Sources" (.subsec/.cov/
// .covleg) a été extrait au lot UI Journal v0.9918 (§3) vers un panneau
// d'annexe distinct, sessionDocSourcesPanelHtml(), rendu après le Roster
// -- ce panneau-ci ne garde que le verdict (jauge), hauteur constante quel
// que soit le nombre de dépôts. Le bilan-note ("X pilotes sur Y...") n'a
// pas de contrepartie dans la maquette (panneau Documentation de l'écran H
// n'en montre aucun, vérifié) : il s'éteint avec le reste du vocabulaire
// générique -- écart signalé, cf rapport.
function sessionDocPanelHtml(s){
  // Lot Jauge ② v0.9928 (brief §7.1) -- dénominateur pessimiste : champs
  // servis par l'API, plus aucun recalcul client (un vol anonyme compte
  // pour un pilote, cf. §3 du brief).
  //
  // ÉCART SIGNALÉ (voir rapport de livraison) : le brief §7.1 donne un
  // calcul `pct` à partir de `s.n_deposited`, mais §6.2 ne liste que trois
  // champs ajoutés au payload GET /sessions/{id} -- n_named, n_anon,
  // doc_ratio -- sans n_deposited. `s.n_deposited` serait donc toujours
  // `undefined` ici. `doc_ratio` (servi, §6.2) porte déjà exactement
  // `n_deposited/denom` -- utilisé ici à la place, résultat identique,
  // aucun champ neuf requis.
  const pct = (s.doc_ratio!=null) ? Math.round(s.doc_ratio*100) : null;
  const pctLabel = pct===null ? "—" : `${pct}%`;
  const pctWidth = pct===null ? 0 : pct;

  return `<div class="framed">
    <div class="sec ink">${escapeHtml(t("session_doc_title"))}</div>
    <div class="gauge">
      <span class="pct ink">${pctLabel}</span>
      <span class="gt ink"><span class="ok" style="width:${pctWidth}%"></span><span class="hatch" style="width:${100-pctWidth}%"></span></span>
      <span class="cap">${escapeHtml(t("session_doc_cap"))}</span>
    </div>
  </div>`;
}

// Lot UI Journal v0.9918 §3 — panneau d'annexe "Sources" (ex-.subsec du
// panneau Documentation), déplacé après le Roster : le verdict (jauge)
// reste avant le Roster, le détail par dépôt vient après, en annexe.
// .cov/.covrow/.covleg réutilisés à l'identique (portés par #view-session,
// zéro règle CSS neuve). Intitulé de section = session_doc_sources, déjà
// au dictionnaire (ex-.subsec).
function sessionDocSourcesPanelHtml(s){
  const normBase = Math.max(0, ...((s.uploads||[]).map(u=> (u.coverage && u.coverage.t_max) || 0)));
  // Lot « Le rattachement des dépôts » (v1.0052) : chaque fichier devient un `.covitem` -- sa ligne (libellé,
  // barre, et « Déplacer… » si can_edit), sa provenance dessous, pour tous, et le panneau de déplacement sous
  // le fichier choisi. La ligne elle-même est celle d'avant (`coverageRow`).
  const items = (s.uploads||[]).map(u=>{
    const act = s.can_edit
      ? `<button type="button" class="btn btn-ghost btn-sm covact" data-move-upload="${escapeAttr(u.id)}">${escapeHtml(t("src_move_cta"))}</button>`
      : "";
    const row = coverageRow(u).replace(/<\/div>$/, act + "</div>");
    const move = (s.can_edit && sessionMoveUploadId === u.id) ? sessionMovePanelHtml(s, u) : "";
    return `<div class="covitem">${row}${sourceProvenanceHtml(u)}${move}</div>`;
  }).join("");
  function coverageRow(u){
    const kindLabel = u.kind==="acmi" ? t("session_cov_kind_acmi") : t("session_cov_kind_debrief");
    const dep = depositorLabel(u.depositor_profile_id);
    const label = `${escapeHtml(kindLabel)} — ${escapeHtml(dep)}`;
    // Révision ④.1 chgt 2 : l'ACMI ne produit pas de `seen_in` sur les
    // events (contrairement aux debriefs) -- sa couverture ne peut donc
    // jamais se déduire de `coverage.t_min/t_max` (toujours "—" pour elle).
    // L'ACMI couvre TOUJOURS l'intégralité de l'enregistrement (0 → durée) :
    // c'est la barre de référence, rendue à 100% sans dépendre de `coverage`.
    if(u.kind === "acmi"){
      return `<div class="covrow"><span class="cl">${label}</span><span class="ct full ink"><i style="left:0;width:100%"></i></span></div>`;
    }
    const cov = u.coverage || {t_min:null, t_max:null, n_events:0};
    if(cov.t_min==null || cov.t_max==null || !normBase){
      return `<div class="covrow"><span class="cl">${label}</span><span class="ct ink"></span></div>`;
    }
    const left = Math.max(0, Math.min(100, (cov.t_min/normBase)*100));
    const width = Math.max(0, Math.min(100-left, ((cov.t_max-cov.t_min)/normBase)*100));
    // Lot M4 (v0.9933) : la demi-teinte marque l'ACMI, pas la couverture.
    // Un débrief couvrant toute la session gardait la classe `full` et
    // devenait indiscernable de l'ACMI (constat du porteur, source Nightjar).
    // `.ct.full` ne désigne plus que l'ACMI, rendue plus haut. Registre R33.
    return `<div class="covrow"><span class="cl">${label}</span><span class="ct ink"><i style="left:${left}%;width:${width}%"></i></span></div>`;
  }

  return `<div class="framed">
    <div class="sec ink">${escapeHtml(t("session_doc_sources"))}</div>
    <div class="cov">${items}</div>
  </div>`;
}

/* ---------- Lot « Le rattachement des dépôts » (v1.0052, R326) : provenance, déplacement, fusion ---------- */

// La ligne de provenance d'un fichier, pour tous : par son titre, par son contenu (l'en-tête nommait…), à la
// main (par qui) ; un fichier rattaché par son seul titre sur l'en-tête d'une mission d'exemple, en rouge.
function sourceProvenanceHtml(u){
  let txt, doute = false;
  if(u.provenance === "manuel"){
    txt = t("src_prov_manuel").replace("{nom}", u.deplace_par ? callsign(u.deplace_par) : "—");
  } else if(u.provenance === "contenu" && u.entete_titre){
    txt = t("src_prov_contenu").replace("{t}", u.entete_titre);
  } else if(u.provenance === "titre" && u.entete_exemple){
    txt = t("src_prov_exemple");
    doute = true;
  } else {
    txt = t("src_prov_titre");
  }
  return `<div class="covnote${doute ? " doute" : ""}">${escapeHtml(txt)}</div>`;
}

function filesWord(n){
  return t("src_move_files").replace("{n}", n).replace("{s}", n > 1 ? "s" : "");
}

// La date longue d'une mission proposée, telle que la maquette l'écrit : « 21 septembre 2026 » (le mois en
// minuscules en français ; `fmtSessionDateFull` le capitalise, l'en-tête le passe en capitales).
function dateLongue(dateStr){
  const d = fmtSessionDateFull(dateStr);
  return currentLang === "fr" ? d.toLowerCase() : d;
}

function jourUtc(dateStr){
  const [y,m,d] = dateStr.split("-").map(Number);
  return Date.UTC(y, m-1, d) / 86400000;
}

// Les autres missions proposées au déplacement et à la fusion (de GET /sessions) : celles dont la date est à
// trois jours au plus de celle de la session, la plus proche d'abord ; une session sans date propose les dix
// missions les plus récentes.
function autresMissions(s){
  const autres = (DEBRIEF_SESSIONS||[]).filter(x=> x.id !== s.id);
  if(!s.mission_date) return autres.slice(0, 10);
  const jour = jourUtc(s.mission_date);
  return autres
    .filter(x=> x.mission_date && Math.abs(jourUtc(x.mission_date) - jour) <= 3)
    .map((x, i)=> ({x, i, ecart: Math.abs(jourUtc(x.mission_date) - jour)}))
    .sort((a, b)=> a.ecart - b.ecart || a.i - b.i)
    .map(o=> o.x);
}

async function ensureAutresMissions(){
  if(missionsLoadState !== "ready" || !DEBRIEF_SESSIONS) await loadMissions();
}

function sessionMovePanelHtml(s, u){
  const dep = depositorLabel(u.depositor_profile_id);
  const titre = t(u.kind === "acmi" ? "src_move_title_acmi" : "src_move_title_debrief").replace("{dep}", dep);
  const autres = autresMissions(s);
  const opts = autres.length
    ? autres.map((x, i)=> `<label class="cm-o"><input type="radio" name="cm-cible" value="${escapeAttr(x.id)}"${i === 0 ? " checked" : ""}>
      <span>${escapeHtml(x.display_title)} <small>· ${escapeHtml(dateLongue(x.mission_date))} · ${escapeHtml(filesWord(x.n_uploads||0))}</small></span></label>`).join("")
    : `<div class="cm-n">${escapeHtml(t("src_move_none"))}</div>`;
  return `<div class="framed covmove">
    <div class="cm-t">${escapeHtml(titre)}</div>
    ${opts}
    <label class="cm-o"><input type="radio" name="cm-cible" value=""${autres.length ? "" : " checked"}><span>${escapeHtml(t("src_move_new"))}</span></label>
    <div class="cm-n">${escapeHtml(t("src_move_note"))}</div>
    <div style="display:flex;gap:.5rem;justify-content:flex-end;margin-top:.6rem">
      <button type="button" class="btn btn-sm" data-move-cancel>${escapeHtml(t("session_edit_cancel"))}</button>
      <button type="button" class="btn btn-sm btn-accent" data-move-go>${escapeHtml(t("src_move_go"))}</button>
    </div>
  </div>`;
}

// Les erreurs : le `detail` de la route pour 409 et 422, sinon le message générique.
function rattachementErreur(e){
  showToast((e && (e.status === 409 || e.status === 422) && e.message) ? e.message : t("error_generic"), "erreur");
}

async function moveUploadGo(btn){
  const choix = $("#session-mount input[name=cm-cible]:checked");
  if(!choix || !sessionMoveUploadId) return;
  if(btn) btn.disabled = true;
  try {
    const res = await apiFetch(`/api/debrief/uploads/${sessionMoveUploadId}/deplacer`, {
      method:"POST", headers:{"Content-Type":"application/json"},
      body: JSON.stringify({session_id: choix.value || null}),
    });
    sessionMoveUploadId = null;
    missionsLoadState = "idle";
    showToast(t("src_move_done"));
    sessionDetailLoadState = "idle";
    if(res.source_supprimee) goDebrief("session", {sessionId: res.session_id});
    else await ensureSessionLoaded(CURRENT_SESSION_ID);
  } catch(e){
    rattachementErreur(e);
    if(btn) btn.disabled = false;
  }
}

// La fusion, dans « Modifier », avant la ligne de boutons : le choix de la mission, puis « Fusionner… », qui
// cède la place à la confirmation. Le bouton « Enregistrer » ne la déclenche jamais.
function sessionMergeFieldHtml(s){
  const autres = autresMissions(s);
  if(sessionMergeChoice && !autres.some(x=> x.id === sessionMergeChoice)){ sessionMergeChoice = ""; sessionMergeConfirm = false; }
  const opts = [`<option value="">${escapeHtml(t("merge_none"))}</option>`].concat(autres.map(x=>
    `<option value="${escapeAttr(x.id)}"${x.id === sessionMergeChoice ? " selected" : ""}>${escapeHtml(x.display_title)} · ${escapeHtml(dateLongue(x.mission_date))}</option>`));
  return `<div class="field">
    <label>${escapeHtml(t("merge_label"))}</label>
    <select id="session-merge-select">${opts.join("")}</select>
    <div id="session-merge-act">${sessionMergeActHtml()}</div>
  </div>`;
}

function sessionMergeActHtml(){
  const x = (DEBRIEF_SESSIONS||[]).find(m=> m.id === sessionMergeChoice);
  if(sessionMergeConfirm && x){
    const n = x.n_uploads||0;
    // Addendum 2 : un seul fichier, une phrase au singulier (`merge_confirm_un`) ; `merge_confirm` à partir de deux.
    const txt = (n === 1 ? t("merge_confirm_un") : t("merge_confirm"))
      .replace("{t}", x.display_title).replace("{n}", n).replace("{s}", n > 1 ? "s" : "");
    return `<div class="merge-confirm">${escapeHtml(txt)}
      <div style="display:flex;gap:.5rem;justify-content:flex-end;margin-top:.5rem">
        <button type="button" class="btn btn-sm" data-merge-cancel>${escapeHtml(t("session_edit_cancel"))}</button>
        <button type="button" class="btn btn-sm btn-accent" data-merge-go>${escapeHtml(t("merge_go"))}</button>
      </div></div>`;
  }
  return `<div style="display:flex;justify-content:flex-end;margin-top:.4rem"><button type="button" class="btn btn-sm" data-merge-cta${sessionMergeChoice ? "" : " disabled"}>${escapeHtml(t("merge_cta"))}</button></div>`;
}

// Redessine la seule zone d'action de la fusion : les champs du panneau gardent ce qu'on y a tapé.
function renderMergeAct(){
  const zone = $("#session-merge-act");
  if(zone) zone.innerHTML = sessionMergeActHtml();
}

async function mergeSessionsGo(btn){
  if(!sessionMergeChoice) return;
  if(btn) btn.disabled = true;
  try {
    await apiFetch(`/api/debrief/sessions/${CURRENT_SESSION_ID}/fusionner`, {
      method:"POST", headers:{"Content-Type":"application/json"},
      body: JSON.stringify({source_id: sessionMergeChoice}),
    });
    sessionMergeChoice = "";
    sessionMergeConfirm = false;
    sessionEditOpen = false;
    missionsLoadState = "idle";
    showToast(t("merge_done"));
    sessionDetailLoadState = "idle";
    await ensureSessionLoaded(CURRENT_SESSION_ID);
  } catch(e){
    rattachementErreur(e);
    if(btn) btn.disabled = false;
  }
}

// Lot 1.5 §3/§4 — tampon "Incomplet", un seul motif (le pilote de CE vol
// n'a pas déposé son propre débrief), porté par le drapeau moteur dédié
// (engine.py stats.pilot_deposited) -- jamais precision_reliability, qui
// replie un second motif (oid manquant) que le tampon ne doit pas affirmer.
function flightIsIncomplete(f){
  return !!(f.stats && f.stats.pilot_deposited === false);
}
function flightStampHtml(f){
  return flightIsIncomplete(f)
    ? `<span class="stamp ink worn">${escapeHtml(t("flight_stamp_incomplete"))}</span>` : "";
}

function rosterBadge(identityState, pilotDeposited){
  // Correctif « vérités du roster » v0.9913 §2 : "nommé" peut venir de la
  // réplication + promotion par profil (décision moteur #3) SANS dépôt
  // effectif du pilote (cas réel mesuré : Kodiak, Francfort, qui cumule
  // "DÉBRIEF DÉPOSÉ" et "INCOMPLET"). La pastille "fiable" exige désormais
  // les deux : identité nommée ET dépôt réel (f.stats.pilot_deposited).
  // Un "nomme" sans dépôt retombe sur "partial" ("Reconstitué"), cohérent
  // avec la note de bas de roster déjà en place et "Précision reconstituée"
  // de la fiche de vol.
  return identityState==="nomme" && pilotDeposited===true ? {cls:"reliable", label:t("session_badge_reliable")}
    : identityState==="rattachable" || identityState==="nomme" ? {cls:"partial", label:t("session_badge_partial")}
    : {cls:"anon", label:t("session_badge_anon")};
}

// Lot 1.4d §6.5 — correspondance directe entre rosterBadge() et le
// vocabulaire .badge2 de la maquette : les trois libellés existants
// (session_badge_reliable/partial/anon) sont verbatim "Débrief déposé" /
// "Reconstitué" / "Vol anonyme", identiques aux trois textes de
// body_missions.html. Aucun nouveau texte, juste le modificateur CSS.
// Correctif v0.9913 : la condition de "reliable" n'est plus le seul
// identity_state==="nomme" -- elle exige en plus pilotDeposited===true
// (cf. rosterBadge ci-dessus). Le mapping verbatim maquette des trois
// libellés reste vrai ; seule la condition d'accès change.
function badge2Mod(cls){
  return cls==="partial" ? "rec" : (cls==="anon" ? "ano" : "");
}

// La maquette n'a que deux états de marqueur (.cm / .cm.hos) contre trois
// côté app (bleu/rouge/inconnu) -- "inconnu" se replie sur le marqueur
// par défaut, écart signalé en rapport (§5.1 cadrage : ce n'est pas un
// troisième état de la DA). L'ancienne fonction coalitionMark() (icônes
// SVG coa-friend/coa-hostile/coa-unknown, vocabulaire .coa-mark éteint
// par ce lot, §4/P8) est retirée : plus aucun appelant.
function cmCls(coalition){
  // A11..A17 (lot Revue de fin de série) : la coalition inconnue est un
  // TROISIÈME état, plus un repli sur le marqueur ami. Ni carré, ni losange.
  if(coalition==="1") return "hos";
  if(coalition==="2") return "";
  return "unk";
}

// .mbr = un mot ("membre"), cf. correctif finitions §1 : le badge de
// carte/table doit tenir sur une ligne au palier compact (360px et
// moins). Le mot court porte l'infobulle (title=) avec le texte long
// (session_member_mark_title), qui reste utile en confirmation au
// survol/tap -- ni retirée, ni redondante avec le visible.
function memberBadgeHtml(isMember){
  return isMember ? ` <span class="mbr" title="${escapeHtml(t("session_member_mark_title"))}">${escapeHtml(t("session_member_mark_short"))}</span>` : "";
}

function rosterRowHtml(f){
  // Groupe à une seule vie (named solo ou anonyme -- brief chgt 1 : "un
  // groupe par vie anonyme") : ligne simple. Conserve data-open-flight
  // (drill par vie) -- interaction sans contrepartie maquette, préservée.
  const isAnon = f.identity_state === "anonyme";
  const nameHtml = isAnon
    ? escapeHtml(anonFlightLabel(f.aircraft_type))
    : escapeHtml(shortCallsign(flightName(f)));
  const timeS = flightDurationS(f);
  const killsN = (f.stats && f.stats.kills) ? f.stats.kills.length : 0;
  const killsDisplay = (killsN===0 && !f.object_id) ? "—" : String(killsN);
  const shotsN = totalShots(f.stats);
  const shotsDisplay = shotsN>0 ? String(shotsN) : "—";
  const issue = flightIssue(f.stats);
  const badge = rosterBadge(f.identity_state, !!(f.stats && f.stats.pilot_deposited));

  return `<tr data-open-flight="${escapeHtml(f.id)}">
    <td><span class="cm ${cmCls(f.coalition)}"></span><span class="pn">${nameHtml}</span>${memberBadgeHtml(!!f.pilote_profile_id)}</td>
    <td class="ac">${acTypeHtml(f.aircraft_type)}</td>
    <td class="num">${fmtDuree(timeS)}</td>
    <td class="num">${killsDisplay}</td>
    <td class="num">${shotsDisplay}</td>
    <td><span class="ro ${issue.key}">${escapeHtml(issue.label)}</span></td>
    <td><span class="badge2 ${badge2Mod(badge.cls)}">${escapeHtml(badge.label)}</span>${flightStampHtml(f)}</td>
  </tr>`;
}

function rosterDetailRowHtml(f, idx){
  // Sous-ligne d'un groupe multi-vies (une par vie du pilote) -- appareil,
  // temps, kills, tirs, issue PAR VIE. Garde data-open-flight (brief §chgt1).
  // Habillage : classe .sub de la maquette (§5.4 -- tr.sub devient
  // l'habillage de la ligne de détail, pas une réplique figée).
  const timeS = flightDurationS(f);
  const killsN = (f.stats && f.stats.kills) ? f.stats.kills.length : 0;
  const killsDisplay = (killsN===0 && !f.object_id) ? "—" : String(killsN);
  const shotsN = totalShots(f.stats);
  const shotsDisplay = shotsN>0 ? String(shotsN) : "—";
  const issue = flightIssue(f.stats);
  const flightLabel = currentLang==="fr" ? `Vol ${idx+1}` : `Flight ${idx+1}`;
  return `<tr class="sub" data-open-flight="${escapeHtml(f.id)}">
    <td>${escapeHtml(flightLabel)}</td>
    <td class="ac">${acTypeHtml(f.aircraft_type)}</td>
    <td class="num">${fmtDuree(timeS)}</td>
    <td class="num">${killsDisplay}</td>
    <td class="num">${shotsDisplay}</td>
    <td><span class="ro ${issue.key}">${escapeHtml(issue.label)}</span></td>
    <td>${flightStampHtml(f)}</td>
  </tr>`;
}

function rosterGroupHeadRowHtml(g){
  const flights = g.flights;
  const rep = bestIdentityFlight(flights);
  const nameHtml = escapeHtml(shortCallsign(flightName(rep)));
  const isMember = flights.some(f=> f.pilote_profile_id);
  const mark = groupCoalition(flights);
  const sumTime = flights.reduce((acc,f)=> acc + (flightDurationS(f)||0), 0);
  const sumKills = flights.reduce((acc,f)=> acc + ((f.stats && f.stats.kills) ? f.stats.kills.length : 0), 0);
  const anyDocumented = flights.some(f=> f.object_id);
  const killsDisplay = (sumKills===0 && !anyDocumented) ? "—" : String(sumKills);
  const sumShots = flights.reduce((acc,f)=> acc + totalShots(f.stats), 0);
  const shotsDisplay = sumShots>0 ? String(sumShots) : "—";
  const distinctAc = new Set(flights.map(f=> f.aircraft_type||"—"));
  const acDisplay = (distinctAc.size===1 ? libTypeHtml([...distinctAc][0]) : "—");
  const nKia = flights.filter(f=> f.stats && (f.stats.crashed || f.stats.pilot_dead)).length;
  const badge = rosterBadge(rep.identity_state, !!(rep.stats && rep.stats.pilot_deposited));
  const expanded = rosterExpandedGroups.has(g.key);
  // Pas de tampon sur une ligne d'en-tête de groupe (rappel non négociable
  // §6.5/§1.10 : un groupe est clé par indicatif, il n'est pas homogène
  // en profil) -- Données porte le badge d'identité seul, sans stamp.
  return `<tr class="rost-group-row${expanded?" is-open":""}" data-group-toggle="${escapeHtml(g.key)}" role="button" tabindex="0" aria-expanded="${expanded}">
    <td><span class="rost-chevron">${SVG_ICON_CHEVRON}</span><span class="cm ${cmCls(mark)}"></span><span class="pn">${nameHtml}</span>${memberBadgeHtml(isMember)}
      <div class="rost-group-meta">${escapeHtml(respawnLabelText(flights.length, nKia))}</div>
    </td>
    <td class="ac">${acDisplay}</td>
    <td class="num">${fmtDuree(sumTime)}</td>
    <td class="num">${killsDisplay}</td>
    <td class="num">${shotsDisplay}</td>
    <td>—</td>
    <td><span class="badge2 ${badge2Mod(badge.cls)}">${escapeHtml(badge.label)}</span></td>
  </tr>`;
}

function rosterGroupRowsHtml(g){
  if(g.flights.length === 1) return rosterRowHtml(g.flights[0]);
  const expanded = rosterExpandedGroups.has(g.key);
  const head = rosterGroupHeadRowHtml(g);
  const details = expanded ? g.flights.map((f,idx)=> rosterDetailRowHtml(f, idx)).join("") : "";
  return head + details;
}

function rosterCardHtml(f){
  const isAnon = f.identity_state === "anonyme";
  const nameHtml = isAnon
    ? escapeHtml(anonFlightLabel(f.aircraft_type))
    : escapeHtml(shortCallsign(flightName(f)));
  const badge = rosterBadge(f.identity_state, !!(f.stats && f.stats.pilot_deposited));
  return `<div class="hc" data-open-flight="${escapeHtml(f.id)}">
    <div class="hpn"><span class="cm ${cmCls(f.coalition)}"></span><span class="pn">${nameHtml}</span>${memberBadgeHtml(!!f.pilote_profile_id)}</div>
    <div class="hrow"><span class="hl">${escapeHtml(t("session_th_aircraft"))}</span>${acTypeHtml(f.aircraft_type)}</div>
    <div class="hrow"><span class="hl">${escapeHtml(t("session_th_time"))}</span>${fmtDuree(flightDurationS(f))}</div>
    <div class="hrow"><span class="hl">${escapeHtml(t("session_th_kills"))}</span>${(f.stats&&f.stats.kills&&f.stats.kills.length)||(!f.object_id?"—":0)}</div>
    <div class="hrow"><span class="hl">${escapeHtml(t("session_th_shots"))}</span>${totalShots(f.stats)>0?totalShots(f.stats):"—"}</div>
    <div class="hrow"><span class="hl">${escapeHtml(t("session_th_issue"))}</span>${escapeHtml(flightIssue(f.stats).label)}</div>
    <div class="hrow"><span class="hl">${escapeHtml(t("session_th_data"))}</span><span class="badge2 ${badge2Mod(badge.cls)}">${escapeHtml(badge.label)}</span>${flightStampHtml(f)}</div>
  </div>`;
}

function rosterDetailCardHtml(f, idx){
  const flightLabel = currentLang==="fr" ? `Vol ${idx+1}` : `Flight ${idx+1}`;
  const killsN = (f.stats && f.stats.kills) ? f.stats.kills.length : 0;
  const killsDisplay = (killsN===0 && !f.object_id) ? "—" : String(killsN);
  return `<div class="hc sub" data-open-flight="${escapeHtml(f.id)}">
    <div class="hrow"><span class="hl">${escapeHtml(flightLabel)}</span>${acTypeHtml(f.aircraft_type)}</div>
    <div class="hrow"><span class="hl">${escapeHtml(t("session_th_time"))}</span>${fmtDuree(flightDurationS(f))}</div>
    <div class="hrow"><span class="hl">${escapeHtml(t("session_th_kills"))}</span>${killsDisplay}</div>
    <div class="hrow"><span class="hl">${escapeHtml(t("session_th_issue"))}</span>${escapeHtml(flightIssue(f.stats).label)}${flightStampHtml(f)}</div>
  </div>`;
}

function rosterGroupCardHtml(g){
  if(g.flights.length === 1) return rosterCardHtml(g.flights[0]);
  const flights = g.flights;
  const rep = bestIdentityFlight(flights);
  const nameHtml = escapeHtml(shortCallsign(flightName(rep)));
  const isMember = flights.some(f=> f.pilote_profile_id);
  const sumTime = flights.reduce((acc,f)=> acc + (flightDurationS(f)||0), 0);
  const sumKills = flights.reduce((acc,f)=> acc + ((f.stats && f.stats.kills) ? f.stats.kills.length : 0), 0);
  const anyDocumented = flights.some(f=> f.object_id);
  const killsDisplay = (sumKills===0 && !anyDocumented) ? "—" : String(sumKills);
  const sumShots = flights.reduce((acc,f)=> acc + totalShots(f.stats), 0);
  const shotsDisplay = sumShots>0 ? String(sumShots) : "—";
  const distinctAc = new Set(flights.map(f=> f.aircraft_type||"—"));
  const acDisplay = (distinctAc.size===1 ? libTypeHtml([...distinctAc][0]) : "—");
  const nKia = flights.filter(f=> f.stats && (f.stats.crashed || f.stats.pilot_dead)).length;
  const badge = rosterBadge(rep.identity_state, !!(rep.stats && rep.stats.pilot_deposited));
  const expanded = rosterExpandedGroups.has(g.key);
  const details = expanded ? flights.map((f,idx)=> rosterDetailCardHtml(f, idx)).join("") : "";
  return `<div class="hc" data-group-toggle="${escapeHtml(g.key)}" role="button" tabindex="0" aria-expanded="${expanded}">
    <div class="hpn"><span class="rost-chevron">${SVG_ICON_CHEVRON}</span><span class="cm ${cmCls(groupCoalition(flights))}"></span><span class="pn">${nameHtml}</span>${memberBadgeHtml(isMember)}</div>
    <div class="hrow"><span class="hl">${escapeHtml(t("session_th_aircraft"))}</span>${acDisplay}</div>
    <div class="hrow"><span class="hl">${escapeHtml(t("session_th_time"))}</span>${fmtDuree(sumTime)}</div>
    <div class="hrow"><span class="hl">${escapeHtml(t("session_th_kills"))}</span>${killsDisplay}</div>
    <div class="hrow"><span class="hl">${escapeHtml(t("session_th_shots"))}</span>${shotsDisplay}</div>
    <div class="hrow"><span class="hl">${escapeHtml(t("session_th_data"))}</span><span class="badge2 ${badge2Mod(badge.cls)}">${escapeHtml(badge.label)}</span></div>
    <div class="rost-group-meta">${escapeHtml(respawnLabelText(flights.length, nKia))}</div>
  </div>${details}`;
}

// Lot 1.4d §6.5 — panneau Roster, vocabulaire DA. .rost pour la table,
// .rost-wrap/.rost-cards pour le couple table/cartes (renommé depuis
// .hebdo-wrap/.hebdo-cards, §5.2 -- ces classes appartiennent à la
// Planification et ne se reprennent jamais). Table et cartes restent
// synchrones : mêmes données, même état de repliement (rosterExpandedGroups
// partagé), P16.
function sessionRosterPanelHtml(s){
  const flights = s.flights||[]; // déjà triés par t_start par l'API -- jamais retriés ici (brief §C.3 : jamais par kills)
  const groups = groupFlightsByPilot(flights);
  const rows = groups.map(rosterGroupRowsHtml).join("");
  const cards = groups.map(rosterGroupCardHtml).join("");
  return `<div class="framed">
    <div class="sec ink">${escapeHtml(t("session_roster_title"))}</div>
    <div class="rost-wrap">
      <table class="rost">
        <tr>
          <th>${escapeHtml(t("session_th_pilot"))}</th><th>${escapeHtml(t("session_th_aircraft"))}</th>
          <th class="num">${escapeHtml(t("session_th_time"))}</th><th class="num">${escapeHtml(t("session_th_kills"))}</th>
          <th class="num">${escapeHtml(t("session_th_shots"))}</th><th>${escapeHtml(t("session_th_issue"))}</th><th>${escapeHtml(t("session_th_data"))}</th>
        </tr>
        ${rows}
      </table>
    </div>
    <div class="rost-cards">${cards}</div>
  </div>`;
}

// Lot 1.4d §6.6 — bilan des destructions, vocabulaire DA (.bcat) : une barre
// par catégorie avec son compte (.v) et son pictogramme (.cic, A18), le
// total en tête du panneau (.tot).
function sessionGraveyardPanelHtml(s, titre){
  // Lot « L'écran B » : un titre facultatif -- l'accueil y nomme sa période.
  // Chgt 3 (révision ④.1) : source = kills_by_category (agrégat serveur des
  // kills validés). `graveyard` reste dans la réponse API (rétro-compat)
  // mais n'est plus lu ici.
  // Lot « Le détecteur et l'hygiène » : l'agrégat exclut les tirs
  // fratricides, par le même calcul que l'écran vol (`_bilan_des_vols`,
  // api.py). Ils sont montrés à part sous les barres, par la même ligne
  // `.frat` et les deux mêmes clés i18n que l'écran vol (R159 étendu).
  const groups = s.kills_by_category || [];
  const frat = s.n_fratricides || 0;
  const maxCount = groups.length ? groups[0].count : 0;
  const rows = groups.map(g=>{
    const width = maxCount>0 ? Math.round((g.count/maxCount)*100) : 0;
    return `<div class="bcat"><span class="cic ${CATEGORY_ICON[g.category] || "target-inconnu"}"></span><span class="c">${escapeHtml(catLabel(g.category))}</span><span class="tk ink"><i style="width:${width}%"></i></span><span class="v">${g.count}</span></div>`;
  }).join("");
  const motFrat = t(frat > 1 ? "flight_kills_frat" : "flight_kills_frat_un");
  const ligneFrat = frat ? `<p class="frat">${frat} ${escapeHtml(motFrat)}</p>` : "";
  return `<div class="framed">
    <div class="sec ink">${escapeHtml(titre || t("session_graveyard_title"))}<b class="tot">${escapeHtml(String(s.n_kills_validated!=null ? s.n_kills_validated : groups.reduce((n,g)=> n+g.count, 0)))}</b></div>
    ${rows}${ligneFrat}
  </div>`;
}

// Lot 1.4d §6.7 — faits saillants, vocabulaire DA (.list/.li, zéro règle
// CSS neuve, §6.7). Les anciennes tuiles de stat (.stat-tile) et le
// paragraphe libre s'éteignent avec le reste du vocabulaire générique ;
// les mêmes données (effectif, répartition, première/dernière
// destruction, catégorie dominante) sont reconduites, reformatées en
// entrées .li (.d = repère court, .t2 = phrase) -- aucune n'est perdue,
// aucune n'est inventée (mêmes calculs qu'avant ce lot).
function sessionFactsPanelHtml(s){
  const flights = s.flights||[];
  const total = flights.length;

  const nBlue = flights.filter(f=> f.coalition==="2").length;
  const nRed = flights.filter(f=> f.coalition==="1").length;
  const nUnknown = total - nBlue - nRed;

  let allKills = [];
  flights.forEach(f=>{
    ((f.stats && f.stats.kills) || []).forEach(k=> allKills.push(k));
  });
  allKills.sort((a,b)=> (a.t||0) - (b.t||0));
  const first = allKills.length ? allKills[0] : null;
  const last = allKills.length ? allKills[allKills.length-1] : null;

  const groups = s.kills_by_category || [];
  const dominant = groups.length ? groups[0] : null;

  const li = (d, t2)=> `<div class="li"><span class="d">${d}</span><span class="t2">${t2}</span></div>`;
  const items = [];
  if(currentLang === "fr"){
    let coaLine = `${nBlue} vols bleus · ${nRed} vols rouges`;
    if(nUnknown>0) coaLine += ` · ${nUnknown} sans camp`;
    items.push(li(String(total), coaLine));
    items.push(li(first ? horodatageHtml(s, first.t) : "—", `Première destruction : ${(first && first.target_unit_type ? libTypeHtml(first.target_unit_type) : "—")}`));
    items.push(li(last ? horodatageHtml(s, last.t) : "—", `Dernière destruction : ${(last && last.target_unit_type ? libTypeHtml(last.target_unit_type) : "—")}`));
    items.push(li(dominant ? String(dominant.count) : "—", `Catégorie dominante détruite : ${escapeHtml(dominant ? catLabel(dominant.category) : "—")}`));
  } else {
    let coaLine = `${nBlue} blue flights · ${nRed} red flights`;
    if(nUnknown>0) coaLine += ` · ${nUnknown} unassigned`;
    items.push(li(String(total), coaLine));
    items.push(li(first ? horodatageHtml(s, first.t) : "—", `First destruction: ${(first && first.target_unit_type ? libTypeHtml(first.target_unit_type) : "—")}`));
    items.push(li(last ? horodatageHtml(s, last.t) : "—", `Last destruction: ${(last && last.target_unit_type ? libTypeHtml(last.target_unit_type) : "—")}`));
    items.push(li(dominant ? String(dominant.count) : "—", `Dominant destroyed category: ${escapeHtml(dominant ? catLabel(dominant.category) : "—")}`));
  }

  // §6.8 — un seul .foot dans tout l'écran, ici, note puis AQAP.
  return `<div class="framed">
    <div class="sec ink">${escapeHtml(t("session_facts_title"))}</div>
    <div class="list">${items.join("")}</div>
    <div class="foot">
      <div class="aqap ink"><b>NATO STANDARD</b><br>AQAP-2110 · ÉD. 4</div>
    </div>
  </div>`;
}

// Lot « Le détecteur et l'hygiène » — les rafales à plusieurs noms d'arme,
// réservées aux éditeurs (R139, R163). La donnée est déjà dans le payload :
// le moteur pose la clé `weapons` sur toute rafale qui mêle plus d'un nom
// d'arme (`engine._compute_bursts`), le critère même de son
// `logging.warning`, que personne ne lit. C'est un signalement, pas un
// verdict : deux journaux nomment peut-être la même arme autrement, ou la
// rafale mêle vraiment deux munitions. Le panneau se tait quand il n'a rien
// à montrer, et le compte précède le nom, comme un emport (« 30 × … ») : un
// nom d'arme peut porter lui-même un nombre (« Bomblets - BLU-18/B x 30,
// HE », seul cas mesuré en production le 28 septembre). Deux arbitrages du
// porteur, 28 septembre. Mobilier du catalogue (.framed/.sec/.list/.li/.note),
// aucune règle CSS neuve.
function sessionMixedBurstsPanelHtml(s){
  if(!s.can_edit) return "";
  const lignes = [];
  (s.flights||[]).forEach(f=>{
    ((f.stats && f.stats.bursts) || []).forEach(b=>{
      if(b.weapons && b.weapons.length > 1) lignes.push({f, b});
    });
  });
  if(!lignes.length) return "";
  lignes.sort((x,y)=> (x.b.t||0) - (y.b.t||0));
  const items = lignes.map(({f, b})=>{
    // Lot « Les référentiels » : ce panneau montre justement les noms BRUTS -- jamais de libellé ici.
    const armes = b.weapons.map(w=> `${w.shots}\u00a0×\u00a0${escapeHtml(w.weapon)}`).join(" · ");
    return `<div class="li"><span class="d">${horodatageHtml(s, b.t)}</span><span class="t2">${escapeHtml(flightLabelOf(f))} — ${armes}</span></div>`;
  }).join("");
  return `<div class="framed">
    <div class="sec ink">${escapeHtml(t("session_mixed_title"))}</div>
    <div class="list">${items}</div>
    <p class="note">${escapeHtml(t("session_mixed_note"))}</p>
  </div>`;
}

function sessionViewHtml(s){
  return sessionHeaderHtml(s)
    + sessionDocPanelHtml(s)
    + sessionRosterPanelHtml(s)
    + sessionDocSourcesPanelHtml(s)
    + sessionMixedBurstsPanelHtml(s)
    + `<div class="duo">${sessionGraveyardPanelHtml(s)}${sessionFactsPanelHtml(s)}</div>`;
}

function openFlight(id){
  goDebrief("flight", {flightId:id});
}

/* ================= Lot D2⑤ : écran Vol (détail par vie, contenu réel) =================
   Markup/CSS repris de la maquette (#screen-flight), scopé #view-flight
   (même discipline que ④ : jamais de redéfinition globale de .panel/.badge/
   etc.). Câblé sur GET /sessions/{id}/flights/{id} (brief Volet C/B) --
   CURRENT_SESSION.flights porte déjà les mêmes stats complètes (chargées
   avec la session), mais le brief demande explicitement le fetch dédié
   (résilience -- fonctionne même si la session n'était pas déjà en cache). */

function flightLabelOf(f){
  return f.identity_state==="anonyme" ? anonFlightLabel(f.aircraft_type) : shortCallsign(flightName(f));
}

// Lot 1.5b §12 — référence verticale .mref, écran Vol. Fonction pure et
// déterministe : une même session donne la même référence à chaque
// affichage, dans les deux langues, après rechargement. Aucun tirage
// aléatoire. Marquage OTAN de decorum, non traduit (repris verbatim de
// la maquette) : pas de clé i18n.
function missionRef(sessionId){
  let h = 0;
  for (let i = 0; i < sessionId.length; i++) h = (h * 31 + sessionId.charCodeAt(i)) % 100000;
  return String(h % 10000).padStart(4, "0");
}

// Lot D — graine du décorum. Fonction pure : une même entité donne la même
// pose à chaque affichage, dans les deux langues, après rechargement.
// AUCUN Math.random() nulle part dans ce lot.
//
// Pourquoi une SECONDE fonction alors que missionRef() existe : missionRef
// est une RÉFÉRENCE AFFICHÉE, bornée à 4 chiffres (% 10000). La réutiliser
// coûterait la moitié de l'entropie ET corrélerait la photo tirée à un
// nombre visible à l'écran. Les deux fonctions ont des rôles disjoints.
function decorumSeed(key){
  let h = 2166136261 >>> 0;                       // FNV-1a 32 bits
  for(let i=0;i<key.length;i++){
    h ^= key.charCodeAt(i);
    h = Math.imul(h, 16777619) >>> 0;
  }
  return h;
}

// Lot D — dérivations du tirage, par décalages sur la même graine
// (brief §8.1). Clé : id d'entité + nom d'écran, ex. `${f.id}|flight`.
// Si photo 2 tombe sur la même valeur que photo 1, on prend
// (photo1+1)%6 -- deux fois la même photo sur une feuille se voit.
function decorumValues(entityId, screenName){
  const h = decorumSeed(`${entityId}|${screenName}`);
  const photo1 = (h >>> 0) % 6;
  let photo2 = (h >>> 3) % 6;
  if(photo2 === photo1) photo2 = (photo1 + 1) % 6;
  return {
    photo1, photo2,
    scotch: (h >>> 8) % 4,
    rot: ((h >>> 12) % 7) - 3,
    crestDx: ((h >>> 16) % 49) - 24,
    crestRot: -4 - ((h >>> 24) % 3),
  };
}

// Rend une pièce photo+scotch (positionClass: "rr-photo" ou "rr-photo-bas").
// Pièce entièrement décorative : alt="", aria-hidden, pointer-events:none
// (porté par la règle CSS partagée .framed>.rr-pc). Budget par palier
// (compact 0, photo-bas wide seul) : géré en CSS pur (data-layout), pas
// ici -- le marquage est toujours émis, jamais conditionné au palier.
function decorumPhotoHtml(f, screenName, positionClass){
  const dv = decorumValues(f.id, screenName);
  const photoIdx = positionClass === "rr-photo-bas" ? dv.photo2 : dv.photo1;
  return `<span class="rr-pc ${positionClass}" style="--rot:${dv.rot}deg" aria-hidden="true">
    <img src="/static/assets/img/rr_photo_${photoIdx+1}.webp" alt="">
    <span class="rr-scotch"><img src="/static/assets/img/rr_scotch_${dv.scotch+1}.webp" alt=""></span>
  </span>`;
}

function updateFlightMref(){
  const el = $("#flight-mref");
  if(!el || !CURRENT_SESSION_ID) return;
  const nnnn = missionRef(String(CURRENT_SESSION_ID));
  const session = (CURRENT_SESSION && CURRENT_SESSION.id === CURRENT_SESSION_ID) ? CURRENT_SESSION : null;
  const idx = session ? (session.flights || []).findIndex(f => f.id === CURRENT_FLIGHT_ID) + 1 : 0;
  el.textContent = idx > 0
    ? mrefText(`MSN/${nnnn}/V${idx}`)
    : mrefText(`MSN/${nnnn}`);
}

// Lot 1.4d §6.1 — référence verticale de l'écran Session. Même fonction
// pure missionRef() que l'écran Vol (jamais une seconde implémentation) ;
// pas de suffixe /Vn ici, Session n'est pas une vie particulière.
function updateSessionMref(){
  const el = $("#session-mref");
  if(!el || !CURRENT_SESSION_ID) return;
  const nnnn = missionRef(String(CURRENT_SESSION_ID));
  el.textContent = mrefText(`MSN/${nnnn}`);
}

async function ensureFlightLoaded(flightId){
  if(!flightId) return;
  // Lot v0.9917 : annuaire du bordereau, en parallèle -- fire-and-forget,
  // guardé en interne (idle/loading/ready/error), no-op si pas admin.
  ensureDebriefMembersLoaded();
  if(CURRENT_FLIGHT && CURRENT_FLIGHT.id === flightId && flightDetailLoadState === "ready"){
    renderFlight();
    return;
  }
  // Correctif v0.9913 §4 : repartir propre en changeant de vol (même
  // discipline que rosterExpandedGroups/sessionEditOpen sur l'écran Session).
  identifyFlightOpen = false;
  slipSelectedProfileId = null;
  flightDetailLoadState = "loading";
  flightDetailError = null;
  renderFlight();
  try {
    CURRENT_FLIGHT = await apiFetch(`/api/debrief/sessions/${CURRENT_SESSION_ID}/flights/${flightId}`);
    flightDetailLoadState = "ready";
    rrChargeFaite("flight", flightId);   // lot « Le retour et l'adresse »
  } catch(e){
    flightDetailLoadState = "error";
    flightDetailError = e.message || t("error_generic");
    if(rrChargeRefusee("flight", flightId, e)) return;   // ouvert par l'adresse : une 4xx ramène à Missions
  }
  renderFlight();
}

// Lot « Le nom qu'on retient » v0.9917 -- annuaire pour le sélecteur du
// bordereau (brief §2/§6). Chargé une seule fois par session d'onglet
// (cache module-level, comme CURRENT_SESSION/CURRENT_FLIGHT), re-rendu au
// besoin quand il arrive après le premier paint du vol. Admin uniquement --
// la route serveur refuse aux autres de toute façon (403), mais on évite
// l'appel réseau pour un compte qui ne verra jamais le bordereau (slipHtml()
// sort tôt sur ME.is_admin, cf. plus bas).
async function ensureDebriefMembersLoaded(){
  if(!(ME && ME.is_admin === true)) return;
  if(debriefMembersLoadState === "ready" || debriefMembersLoadState === "loading") return;
  debriefMembersLoadState = "loading";
  try {
    const data = await apiFetch(`/api/debrief/members`);
    DEBRIEF_MEMBERS = data.members || [];
    debriefMembersLoadState = "ready";
  } catch(e){
    debriefMembersLoadState = "error";
    DEBRIEF_MEMBERS = [];
  }
  renderFlight();
}

// Lot 1.5 §2.1 — squelette de chargement de l'écran Vol. Les quatre
// intitulés de section (constantes i18n, connus avant la donnée) se
// dessinent pour de vrai, sans silhouette d'appareil : le squelette ne
// connaît pas encore l'appareil du vol. L'idbar (donnée : indicatif,
// issue, type, badge) et les corps de bloc portent des .bar.
function flightSkeletonHtml(){
  return `<div class="idbar">
    <div>
      <div class="kick"><span class="bar" style="width:9rem"></span></div>
      <div class="callsign"><span class="bar" style="width:12rem;height:2rem"></span></div>
    </div>
    <div class="meta"><span class="bar" style="width:5rem"></span></div>
  </div>
  <div class="rule2 ink"></div>

  <div class="framed">
    <div class="sec ink">${escapeHtml(t("flight_summary_title"))}</div>
    <div class="stats">
      <div class="stat"><div class="v"><span class="bar" style="width:2.2rem"></span></div><div class="l">${escapeHtml(t("flight_stat_kills"))}</div></div>
      <div class="stat"><div class="v"><span class="bar" style="width:2.2rem"></span></div><div class="l">${escapeHtml(t("flight_stat_time"))}</div></div>
      <div class="stat"><div class="v"><span class="bar" style="width:2.2rem"></span></div><div class="l">${escapeHtml(t("flight_stat_altmax"))}</div></div>
      <div class="stat"><div class="v"><span class="bar" style="width:2.2rem"></span></div><div class="l">${escapeHtml(t("flight_stat_bilan"))}</div></div>
    </div>
  </div>

  <div class="framed">
    <div class="sec ink">${escapeHtml(t("flight_timeline_title"))}</div>
    <span class="bar" style="width:100%"></span>
  </div>

  <div class="duo">
    <div class="framed">
      <div class="sec ink">${escapeHtml(t("flight_precision_title"))}</div>
      <span class="bar" style="width:100%"></span>
    </div>
    <div class="framed">
      <div class="sec ink">${escapeHtml(t("flight_threats_title"))}</div>
      <span class="bar" style="width:100%"></span>
    </div>
  </div>`;
}

// Lot D — écusson de la fiche de vol. Deux emplacements depuis le
// correctif v0.9947 §5 : la bande haute (#flight-crest, enfant direct de
// .sheet, hors de #flight-mount) et le badge compact (#flight-crest-compact,
// enfant du cadre Synthèse, DANS #flight-mount -- recréé à chaque rendu de
// flightViewHtml()). Même image, même tirage aux deux emplacements
// (decorumValues(f.id,"flight") appelé une seule fois). f.crest nul -> les
// DEUX emplacements restent vides, jamais une image cassée.
function updateFlightCrest(f){
  const elHaut = $("#flight-crest");
  const elCompact = $("#flight-crest-compact");
  if(!f || !f.crest){
    if(elHaut){ elHaut.hidden = true; elHaut.innerHTML = ""; }
    if(elCompact){ elCompact.innerHTML = ""; }
    return;
  }
  const dv = decorumValues(f.id, "flight");
  const imgHtml = `<img src="/api/squadrons/${f.crest.squadron_id}/crest?v=${encodeURIComponent(f.crest.crest_sha)}" alt="">`;
  if(elHaut){
    elHaut.hidden = false;
    elHaut.style.setProperty("--crest-dx", `${dv.crestDx}px`);
    elHaut.style.setProperty("--crest-rot", `${dv.crestRot}deg`);
    elHaut.innerHTML = imgHtml;
  }
  if(elCompact){
    elCompact.innerHTML = imgHtml;
  }
}

function renderFlight(){
  // Lot 1.5b §12 : référence verticale, recalculée à chaque rendu -- se
  // stabilise dès que CURRENT_SESSION (et donc l'indice du vol) est chargé.
  updateFlightMref();

  const mount = $("#flight-mount");
  if(!mount) return;

  if(flightDetailLoadState === "loading" && !(CURRENT_FLIGHT && CURRENT_FLIGHT.id===CURRENT_FLIGHT_ID)){
    mount.innerHTML = flightSkeletonHtml();
    updateFlightCrest(null);
    return;
  }
  if(flightDetailLoadState === "error"){
    mount.innerHTML = `<div class="state fail">
      <p>${escapeHtml(flightDetailError || t("error_generic"))}</p>
      <button type="button" class="btn btn-sm" data-flight-retry>${escapeHtml(t("session_error_retry"))}</button>
    </div>`;
    updateFlightCrest(null);
    return;
  }
  if(!CURRENT_FLIGHT || CURRENT_FLIGHT.id !== CURRENT_FLIGHT_ID){
    mount.innerHTML = flightSkeletonHtml();
    updateFlightCrest(null);
    return;
  }

  const f = CURRENT_FLIGHT;
  mount.innerHTML = flightViewHtml(f);
  updateFlightCrest(f);
}

/* ---------- Helpers de formatage propres à la vue Vol ---------- */

// Lot « L'heure et la durée » v0.9995 (arbitrage du porteur du 17/09, option A) :
// un instant d'évènement du module Débrief se dit par DEUX valeurs, sans
// secondes -- l'heure de Paris (fuseau de l'escadrille, le même que la fiche
// du Récit) et la durée écoulée depuis le début de mission. Remplacent
// fmtElapsedFull (h:mm:ss) et fmtElapsedHM (h:mm), restés sans appelant.
function fmtTplus(s){
  // Lot « Durée » v0.9996 : "t+" suivi de l'écriture unique (fmtDuree).
  return s==null ? "—" : `t+${fmtDuree(s)}`;
}

function refTimeMs(referenceTime){
  // `reference_time` arrive avec six décimales de seconde ; on les ramène à
  // trois avant Date(), dont l'analyse au-delà de trois n'est pas normée.
  if(!referenceTime) return NaN;
  return new Date(String(referenceTime).replace(/(\.\d{3})\d+/, "$1")).getTime();
}

// Lot « Les heures de jour et de nuit » (v1.0068) : `ancre` est la SESSION qui
// dit l'instant (ou null) -- elle porte `horloge_mission_s` (l'heure de la
// mission à t = 0) et `reference_time`. Elle a une heure à dire quand l'une des
// deux est connue ; `fmtInstant` est le seul endroit qui décide laquelle.
function ancreDeLHeure(ancre){
  return !!ancre && (ancre.horloge_mission_s != null || !isNaN(refTimeMs(ancre.reference_time)));
}

function fmtInstant(ancre, s){
  // Instant dit dans une phrase : l'heure de la mission (`horloge_mission_s`
  // + s, modulo 24 h : "07h26", "07:26" en anglais) quand la session porte son
  // horloge, sinon l'heure de Paris ("22h12", "22:12" en anglais) si elle
  // porte son ancre, sinon la durée seule -- jamais une heure inventée.
  if(!ancreDeLHeure(ancre) || s==null) return fmtTplus(s);
  let hm;
  if(ancre.horloge_mission_s != null){
    const x = (((ancre.horloge_mission_s + s) % 86400) + 86400) % 86400;
    const deux = n => String(n).padStart(2, "0");
    hm = `${deux(Math.floor(x / 3600))}:${deux(Math.floor((x % 3600) / 60))}`;
  } else {
    hm = fmtParisTime(new Date(refTimeMs(ancre.reference_time) + s*1000).toISOString());
  }
  return currentLang === "fr" ? hm.replace(":", "h") : hm;
}

function horodatageHtml(ancre, s){
  // Cellule d'horodatage (journal, Menaces subies, Faits marquants, Brut) :
  // .hm (heure) puis .tp (durée) ; .tp seule sans heure à dire.
  const tp = `<span class="tp">${fmtTplus(s)}</span>`;
  if(!ancreDeLHeure(ancre) || s==null) return tp;
  return `<span class="hm">${fmtInstant(ancre, s)}</span>${tp}`;
}

function flightRefTime(){
  // Ancre de la session du vol affiché -- la session elle-même (lot « Les
  // heures de jour et de nuit » : elle porte l'horloge de la mission et
  // l'ancre de Paris) ; null si la session chargée n'est pas celle du vol
  // (même garde que .kick dans flightViewHtml).
  return (CURRENT_SESSION && CURRENT_SESSION.id === CURRENT_SESSION_ID) ? CURRENT_SESSION : null;
}

function fmtFileSize(bytes){
  if(bytes == null || isNaN(bytes)) return "";
  const fr = currentLang === "fr";
  if(bytes < 1024) return fr ? `${bytes} o` : `${bytes} B`;
  if(bytes < 1024*1024) return `${Math.round(bytes/1024)} ${fr ? "Ko" : "KB"}`;
  const mo = (bytes/(1024*1024)).toFixed(1);
  return `${fr ? mo.replace(".", ",") : mo} ${fr ? "Mo" : "MB"}`;
}

function fmtAltM(v){
  if(v==null) return null;
  return Math.round(v).toLocaleString(currentLang==="fr" ? "fr-FR" : "en-US");
}

function phaseLabel(type){
  return t("flight_phase_" + String(type||"").replace(/\s+/g,"_"));
}

// gravite (visé/touché/abattu) : enum FR fixe côté moteur (cf. engine.py,
// jamais modifié ici) -- traduite ici uniquement pour l'affichage EN, à la
// façon des libellés d'issue (session_issue_*), pas laissée FR-fixe comme
// les catégories du référentiel categorize (unités, hors périmètre front).
function graviteLabel(g){
  if(g==="abattu") return t("flight_grav_down");
  if(g==="touché") return t("flight_grav_hit");
  return t("flight_grav_aimed");
}
function graviteSevClass(g){
  return g==="abattu" ? "down" : (g==="touché" ? "hit" : "aimed");
}

// Écart signalé / correctif découvert en recette sur données réelles
// (session Foothold) : un engagement continu (tir canon soutenu, débris de
// collision) peut produire des MILLIERS d'entrées `threat_log` "touché"
// quasi simultanées pour la même paire tireur/arme (jusqu'à ~3700 sur un
// seul vol de l'échantillon réel) -- un rendu 1 ligne par entrée brute est
// totalement illisible, en Journal du vol comme en Menaces subies/Rapport.
// Regroupées ici en "salves" : même tireur + même arme + même gravité,
// écart <= 5s entre deux impacts consécutifs -> une seule entrée agrégée
// (avec compteur). Aucune métrique inventée (§11.7) : juste un
// regroupement de faits identiques rapprochés dans le temps.
function aggregateThreatLog(log){
  const WINDOW_S = 5;
  const sorted = (log||[]).slice().sort((a,b)=> (a.t||0)-(b.t||0));
  const groups = [];
  sorted.forEach(th=>{
    const last = groups[groups.length-1];
    if(last && last.initiator_object_id===th.initiator_object_id && last.weapon===th.weapon
       && last.gravite===th.gravite && ((th.t||0) - last.tEnd) <= WINDOW_S){
      last.tEnd = th.t||0;
      last.count += 1;
    } else {
      groups.push({
        t: th.t||0, tEnd: th.t||0, count: 1,
        initiator_object_id: th.initiator_object_id,
        initiator_unit_type: th.initiator_unit_type,
        weapon: th.weapon, gravite: th.gravite,
      });
    }
  });
  return groups;
}

function flightHeaderName(f){
  return f.identity_state==="anonyme" ? anonFlightLabel(f.aircraft_type) : shortCallsign(flightName(f));
}

/* ---------- .idbar > .meta (AVENANT_1 §C, écart E2) ----------
   .ac et .badge portent des DONNÉES réelles (type d'appareil, fiabilité
   d'identification) que la maquette ne prévoit pas -- "la maquette
   n'arbitre jamais le contenu" (registre §5). Relogées ici depuis
   l'ancien page-head/lede, ni supprimées ni restylées (classes et CSS
   inchangés). Le type est omis pour un vol anonyme : anonFlightLabel()
   l'inclut déjà dans .callsign ("Vol Mi-24P anonyme"), le répéter
   doublonnerait -- même garde-fou que l'ancien flightHeaderSuffix
   (écart VOLET C), reconduit ici à l'identique. */
function flightMetaHtml(f){
  const badge = rosterBadge(f.identity_state, !!(f.stats && f.stats.pilot_deposited));
  const badgeHtml = `<span class="badge ${badge.cls}">${escapeHtml(badge.label)}</span>`;
  const typeHtml = f.identity_state === "anonyme" ? "" : `<b class="ac">${acTypeHtml(f.aircraft_type)}</b>`;
  return `${typeHtml}${badgeHtml}`;
}

function killLineHtml(k){
  // Écart signalé : l'ancien <span class="tgt"> n'a pas d'équivalent dans
  // le vocabulaire maquette (.tx est du texte simple, cf Porte 4) -- la
  // cible n'est plus mise en exergue typographiquement, juste nommée.
  const tgt = k.target_unit_type ? libTypeHtml(k.target_unit_type) : "—";
  const wpn = k.weapon ? libArmeHtml(k.weapon) : null;
  // Lot UI Journal v0.9918 §4 : suffixe "touché à …" -- N'APPARAÎT
  // QUE si stats.kills[*].impact_t est présent (moteur recalculé). Sur une
  // session non recalculée le champ est absent et cette ligne reste
  // caractère pour caractère celle du v0.9917 (porte de dégradation P2).
  // Lot « L'heure et la durée » v0.9995 : l'instant se dit à la minute, et le
  // suffixe se tait quand il répèterait celui de la ligne elle-même.
  const refTime = flightRefTime();
  const impactAt = k.impact_t != null ? fmtInstant(refTime, k.impact_t) : null;
  const impactSuffix = (impactAt != null && impactAt !== fmtInstant(refTime, k.t))
    ? (currentLang === "fr" ? ` · touché à ${impactAt}` : ` · hit at ${impactAt}`)
    : "";
  // Lot « Le journal dit quand un tir touche » : un kill par l'explosion d'une
  // épave nomme l'épave et l'heure de sa destruction ; sans `explosion`, rien.
  const ex = k.explosion;
  const exSuffix = ex
    ? (currentLang === "fr"
        ? ` · explosion du ${(ex.wreck ? libTypeHtml(ex.wreck) : "—")} détruit à ${fmtInstant(refTime, ex.wreck_t)}`
        : ` · explosion of the ${(ex.wreck ? libTypeHtml(ex.wreck) : "—")} destroyed at ${fmtInstant(refTime, ex.wreck_t)}`)
    : "";
  if(currentLang === "fr"){
    return (wpn ? `Détruit ${tgt} au ${wpn}` : `Détruit ${tgt}`) + impactSuffix + exSuffix;
  }
  return (wpn ? `Destroyed ${tgt} with ${wpn}` : `Destroyed ${tgt}`) + impactSuffix + exSuffix;
}

// Lot « Le journal dit quand un tir touche » : le tampon COLLATÉRAL d'un kill
// par l'explosion d'une épave, au gabarit du tampon COLLABORATION -- "" sans
// `explosion`.
function killCollateralTag(k){
  return k.explosion ? `<span class="tg co">${escapeHtml(t("flight_tag_collateral"))}</span>` : "";
}

// Lot Moteur D2①/D4 : pastille "collaboration" + sous-ligne, quand
// stats.kills[*].also_engaged_by (engine.py _compute_also_engaged_by)
// porte au moins un co-engageur. Purement additif -- {extraTag:"",sub:""}
// si le champ est absent/vide, la ligne de kill reste inchangée.
// L'indicatif est déjà réduit au segment côté moteur (_flight_display_label) --
// pas de retraitement ici, seulement l'habillage <span class="who">.
function killCollabHtml(k){
  const co = k.also_engaged_by;
  if(!co || !co.length) return {extraTag:"", sub:""};
  const extraTag = `<span class="tg co">${escapeHtml(t("flight_tag_collab"))}</span>`;
  const parts = co.map(c=>{
    const who = `<span class="who">${escapeHtml(c.pilot)}</span>`;
    const wpn = c.weapon
      ? (currentLang==="fr" ? ` au ${libArmeHtml(c.weapon)}` : ` with ${libArmeHtml(c.weapon)}`)
      : "";
    const time = fmtInstant(flightRefTime(), c.t);
    return currentLang === "fr"
      ? `Touché par ${who}${wpn} — ${time}`
      : `Hit by ${who}${wpn} — ${time}`;
  });
  // Brief §6 (D4) : plusieurs co-engageurs se séparent par " · ", DANS le
  // même <span class="tx2"> -- pas une sous-ligne par co-engageur.
  const sub = `<div class="tlsub co-hit"><span class="fl">↳</span><span class="tx2">${parts.join(" · ")}</span></div>`;
  return {extraTag, sub};
}

// Lot UI Journal v0.9918 §5 : une ligne de journal par rafale de tirs
// (stats.bursts, engine.py _compute_bursts). Même vocabulaire que
// threatLineHtml -- un tir isolé (shots===1) reste une ligne simple, SANS
// multiplicateur (brief §5, "un tir isolé reste une ligne simple").
// Lot « Le journal dit quand un tir touche » : les cibles d'une ligne
// (`targets`), `n` devant le type quand il dépasse 1.
function burstTargetsText(targets){
  return (targets||[]).map(x => (x.n > 1 ? `${x.n} ` : "") + (x.type ? libTypeHtml(x.type) : "—"))
    .join(currentLang==="fr" ? " · " : ", ");
}

// Lot « Le journal dit quand un tir touche » : « — [N] au but sur … ».
function burstOnTargetText(n, tgts){
  const nb = n ? `${n} ` : "";
  if(currentLang === "fr") return ` — ${nb}au but${tgts ? ` sur ${tgts}` : ""}`;
  return ` — ${nb}on target${tgts ? `: ${tgts}` : ""}`;
}

// Lot « Le journal dit quand un tir touche » : une ligne de canon -- ses
// pressions de détente rapprochées, ses obus, ses obus au but et leurs cibles.
function cannonLineHtml(b){
  const wpn = b.weapon ? libArmeHtml(b.weapon) : "—";
  const fr = currentLang === "fr";
  const obus = fr ? `${b.rounds} obus` : `${b.rounds} ${b.rounds === 1 ? "round" : "rounds"}`;
  const compte = b.shots > 1 ? (fr ? `${b.shots} rafales, ${obus}` : `${b.shots} bursts, ${obus}`) : obus;
  const auBut = b.rounds_hit > 0 ? burstOnTargetText(b.rounds_hit, burstTargetsText(b.targets)) : "";
  return `${wpn} · ${compte}${auBut}`;
}

function burstLineHtml(b, sw){
  if(b.cannon) return cannonLineHtml(b);
  const wpn = b.weapon ? libArmeHtml(b.weapon) : "—";
  // Lot « Le journal dit quand un tir touche » : une ligne qui porte `targets`
  // dit « au but » ; sans `targets`, ou sans tir au but, la ligne d'avant.
  const neuf = Array.isArray(b.targets);
  const tgtsNeuf = neuf ? burstTargetsText(b.targets) : "";
  const mixte = !!(b.weapons && b.weapons.length > 1);
  const mixteParts = mixte ? b.weapons.map(w => `${w.shots} × ${libArmeHtml(w.weapon)}`).join(" · ") : "";
  const tete = mixte
    ? (currentLang === "fr" ? `${b.shots} tirs : ${mixteParts}` : `${b.shots} shots: ${mixteParts}`)
    : (b.shots > 1 ? `${b.shots} × ${wpn}` : wpn);
  if(neuf && b.salvo && b.targets.length){
    return tete + burstOnTargetText(0, tgtsNeuf);
  }
  if(neuf && !b.salvo && b.hits > 0){
    return tete + burstOnTargetText(b.shots > 1 ? b.hits : 0, tgtsNeuf);
  }
  // Lot « L'écran de la précision » : une rafale d'une seule arme à sous-munitions
  // (`salvos` dans `shots_by_weapon`) s'arrête au nom de l'arme -- une sous-munition
  // n'est jamais liée à son largage, son « 0 touche » ne disait rien.
  const wSalves = !(b.weapons && b.weapons.length > 1) && b.weapon && sw && sw[b.weapon] && sw[b.weapon].salvos != null;
  if(wSalves){
    return b.shots > 1 ? `${b.shots} × ${wpn}` : wpn;
  }
  const tgts = (b.target_unit_types||[]).map(cle => libTypeHtml(cle)).join(currentLang==="fr" ? " · " : ", ");
  const tgtPart = tgts ? (currentLang==="fr" ? ` sur ${tgts}` : ` on ${tgts}`) : "";
  const hitWord = currentLang==="fr"
    ? (b.hits>1 ? "touches" : "touche")
    : (b.hits===1 ? "hit" : "hits");
  // Lot Journal v0.9941 §6, Forme B (arbitrée par le porteur) : une rafale
  // portant `weapons` (engine.py _compute_bursts, geste ③) mêle plusieurs
  // munitions -- répartition par arme, séparateur ` · ` dans les DEUX
  // langues (le séparateur d'armes ne suit pas la langue ; seuls `tgts`
  // et la ponctuation d'en-tête la suivent). Le cas `shots === 1` est
  // impossible par construction (une rafale d'un tir n'a qu'une arme).
  if(b.weapons && b.weapons.length > 1){
    const parts = b.weapons.map(w => `${w.shots} × ${libArmeHtml(w.weapon)}`).join(" · ");
    return currentLang === "fr"
      ? `${b.shots} tirs : ${parts} — ${b.hits} ${hitWord}${tgtPart}`
      : `${b.shots} shots: ${parts} — ${b.hits} ${hitWord}${tgtPart}`;
  }
  if(b.shots > 1){
    return currentLang === "fr"
      ? `${b.shots} × ${wpn} — ${b.hits} ${hitWord}${tgtPart}`
      : `${b.shots} × ${wpn} — ${b.hits} ${hitWord}${tgtPart}`;
  }
  // Tir isolé : pas de multiplicateur, phrasé comme une ligne de menace.
  const hitPart = b.hits > 0
    ? (currentLang==="fr" ? ` — 1 touche${tgtPart}` : ` — 1 hit${tgtPart}`)
    : "";
  return `${wpn}${hitPart}`;
}

// Lot Moteur D2②/D5 : une sous-ligne PAR CIBLE quand stats.bursts[*].
// destroyed_by_other (engine.py _compute_destroyed_by_other) porte au
// moins une entrée -- cibles touchées par cette rafale, non abattues par
// CE vol, mais détruites par un autre humain. Contrairement à D4, pas de
// pastille sur la ligne de rafale elle-même : la pastille "destruction"
// vit DANS chaque sous-ligne (cf. CSS `.tlsub .tg.co`).
function burstDestroyedByOtherHtml(b){
  const dbo = b.destroyed_by_other;
  if(!dbo || !dbo.length) return "";
  return dbo.map(d=>{
    const tgt = d.target_unit_type ? libTypeHtml(d.target_unit_type) : "—";
    const who = `<span class="who">${escapeHtml(d.killer)}</span>`;
    const wpn = d.killer_weapon
      ? (currentLang==="fr" ? ` au ${libArmeHtml(d.killer_weapon)}` : ` with ${libArmeHtml(d.killer_weapon)}`)
      : "";
    const time = fmtInstant(flightRefTime(), d.kill_t);
    const text = currentLang === "fr"
      ? `${tgt} détruit par ${who}${wpn} à ${time}`
      : `${tgt} destroyed by ${who}${wpn} at ${time}`;
    return `<div class="tlsub"><span class="tg co">${escapeHtml(t("flight_tag_destruction"))}</span><span class="tx2">${text}</span></div>`;
  }).join("");
}

// Lot « Le journal dit quand un tir touche » : l'issue de chaque cible
// touchée (`outcomes`), au gabarit des sous-lignes DESTRUCTION -- détruite
// par un autre, créditée à qui l'a détruite (une explosion n'est pas dite),
// ou touchée et non détruite (pastille `in`). Sans `outcomes`, les
// sous-lignes d'avant (`burstDestroyedByOtherHtml`).
function burstOutcomesHtml(b){
  if(!Array.isArray(b.outcomes)) return burstDestroyedByOtherHtml(b);
  const fr = currentLang === "fr";
  return b.outcomes.map(o=>{
    const tgt = o.type ? libTypeHtml(o.type) : "—";
    if(o.issue === "intact"){
      const text = o.n > 1
        ? (fr ? `${o.n} ${tgt} touchés, non détruits` : `${o.n} ${tgt} hit, not destroyed`)
        : (fr ? `${tgt} touché, non détruit` : `${tgt} hit, not destroyed`);
      return `<div class="tlsub"><span class="tg in">${escapeHtml(t("flight_tag_touche"))}</span><span class="tx2">${text}</span></div>`;
    }
    const par = o.by
      ? (fr ? ` par <span class="who">${escapeHtml(o.by)}</span>` : ` by <span class="who">${escapeHtml(o.by)}</span>`)
      : (o.by_unit_type ? (fr ? ` par un ${libTypeHtml(o.by_unit_type)}` : ` by a ${libTypeHtml(o.by_unit_type)}`) : "");
    const wpn = (!o.explosion && o.by_weapon)
      ? (fr ? ` au ${libArmeHtml(o.by_weapon)}` : ` with ${libArmeHtml(o.by_weapon)}`)
      : "";
    const time = fmtInstant(flightRefTime(), o.t);
    const text = fr
      ? `${tgt} endommagé détruit${par}${wpn} à ${time}`
      : `damaged ${tgt} destroyed${par}${wpn} at ${time}`;
    return `<div class="tlsub"><span class="tg co">${escapeHtml(t("flight_tag_destruction"))}</span><span class="tx2">${text}</span></div>`;
  }).join("");
}

function threatLineHtml(g){
  const src = g.initiator_unit_type ? libTypeHtml(g.initiator_unit_type) : "—";
  const wpn = g.weapon ? libArmeHtml(g.weapon) : null;
  const grav = escapeHtml(graviteLabel(g.gravite));
  const suffix = g.count>1 ? ` (×${g.count})` : "";
  if(currentLang === "fr"){
    return (wpn ? `${grav} par ${src} au ${wpn}` : `${grav} par ${src}`) + suffix;
  }
  return (wpn ? `${grav} by ${src} with ${wpn}` : `${grav} by ${src}`) + suffix;
}

/* ---------- Journal du vol (fusion phases + kills + menaces, triée par t) ---------- */

function flightTimelineItems(f){
  const stats = f.stats || {};
  const items = [];
  // Correctif visuel (Lot Fusion, retour du porteur 15/09) : les phases
  // repliées en "saut" (touch-and-go, geste 4) ne s'affichent PAS dans le
  // journal -- ni comme atterrissage/décollage séparés (c'est tout
  // l'objet du repli côté moteur), ni comme une ligne "Saut" dédiée.
  // Elles restent dans `stats.phases` (comptes réels takeoffs/landings
  // inchangés, `au_sol_s` disponible pour un usage futur) -- seul le
  // rendu du journal les ignore.
  (stats.phases||[]).forEach(p=>{
    if(p.type === "saut") return;
    items.push({t: p.t||0, cls:"phase", tag: t("flight_tag_phase"), html: escapeHtml(phaseLabel(p.type))});
  });
  (stats.kills||[]).forEach(k=>{
    const collab = killCollabHtml(k);
    items.push({t: k.t||0, cls:"kill", tag: t("flight_tag_kill"), html: killLineHtml(k),
                extraTag: killCollateralTag(k) + collab.extraTag, sub: collab.sub});
  });
  // Lot UI Journal v0.9918 §5 : rafales groupées, étiquette neutre (cls
  // "shot" -- timelineTagCls() ne la reconnaît pas et retombe sur "" par
  // défaut, donc .tg SANS variante, pas de .k ni de .m -- brief §5).
  (stats.bursts||[]).forEach(b=>{
    items.push({t: b.t||0, cls:"shot", tag: t("flight_tag_shot"), html: burstLineHtml(b, stats.shots_by_weapon),
                extraTag: "", sub: burstOutcomesHtml(b)});
  });
  aggregateThreatLog(stats.threat_log).forEach(g=>{
    items.push({t: g.t||0, cls:"threat", tag: t("flight_tag_threat"), html: threatLineHtml(g)});
  });
  items.sort((a,b)=> a.t - b.t);
  return items;
}

// tag kill/menace -> .tg.k / .tg.m ; phase = .tg nu (brief §4, table de
// correspondance) -- it.cls vient de flightTimelineItems ci-dessus.
function timelineTagCls(cls){
  return cls==="kill" ? " k" : (cls==="threat" ? " m" : "");
}

function flightTimelineHtml(f){
  const items = flightTimelineItems(f);
  if(items.length === 0){
    return `<div class="note">${escapeHtml(t("flight_timeline_empty"))}</div>`;
  }
  // Lot Moteur D4/D5 : `it.extraTag` (pastille "collaboration" sur la ligne
  // de kill) et `it.sub` (sous-ligne(s) sous la ligne, collaboration ou
  // destruction) sont additifs -- "" pour tout item qui n'en porte pas
  // (phase/menace/rafale-sans-destroyed_by_other), la ligne reste alors
  // caractère pour caractère celle d'avant ce lot.
  const refTime = flightRefTime();
  return `<div class="tl">` + items.map(it=>
    `<div class="tlrow"><span class="tt2">${horodatageHtml(refTime, it.t)}</span><span class="tg${timelineTagCls(it.cls)}">${escapeHtml(it.tag)}</span>${it.extraTag||""}<span class="tx">${it.html}</span></div>${it.sub||""}`
  ).join("") + `</div>`;
}

/* ---------- Silhouette de l'appareil du vol ---------- */

// Lot « L'appareil du vol » — la silhouette de l'appareil du vol, à gauche des
// titres de l'écran vol (.ic.wire), à la place du Mi-24 unique posé au lot 1.5.
// Sept silhouettes pleines (Gemini, conditionnées le 28 septembre) : à 30 × 15 px,
// seule une silhouette pleine distingue un appareil d'un autre. Un appareil hors
// de cette liste n'en montre aucune — un mauvais appareil trompe plus qu'une
// absence (deux arbitrages du porteur, 28 septembre). Le type DCS est reconnu par
// son préfixe : « Mi-24P » et « Mi-24V » partagent la même silhouette.
const AIRCRAFT_SILHOUETTE = [
  [/^Mi-24/, "mi24"],
  [/^Mi-8/, "mi8"],
  [/^F-4E/, "f4e"],
  [/^Mirage-F1/, "f1"],
  [/^UH-1/, "uh1"],
  [/^F-16/, "f16"],
  [/^F-5E/, "f5"],
];
function aircraftSilhouetteHtml(aircraftType){
  const hit = AIRCRAFT_SILHOUETTE.find(([re]) => re.test(aircraftType || ""));
  return hit ? `<span class="ic wire ac-${hit[1]}"></span>` : "";
}

/* ---------- Précision par arme ---------- */

// Lot « L'écran de la précision » : les armes rangées par type, dans cet ordre. La famille vient du moteur
// (`stats.weapon_families` au Vol, `familles` au Dossier) ; le canon a son type ; toute autre famille, ou une
// famille inconnue, tombe dans « Autres ». Partagé par l'écran Vol et le Dossier.
const PREC_TYPES = [
  {cle: "prec_cat_missiles", familles: [7, 8, 11]},
  {cle: "prec_cat_roquettes", familles: [33]},
  {cle: "prec_cat_bombes", familles: [9, 36]},
  {cle: "prec_cat_sousmun", familles: [38]},
  {cle: "prec_cat_canon", familles: []},
  {cle: "prec_cat_autres", familles: []},
];
function precTypeCle(famille){
  const type = PREC_TYPES.find(ty => ty.familles.includes(famille));
  return type ? type.cle : "prec_cat_autres";
}
// Le singulier : n ≤ 1 en français, n = 1 en anglais.
function precNombre(n, cleUn, cleN){
  const un = currentLang === "fr" ? n <= 1 : n === 1;
  return t(un ? cleUn : cleN).replace("{n}", n);
}
// Ce que comptent les nombres : « 16 conteneurs largués en 1 salve » ; « 250 obus en 31 rafales · 5 rafales au but ».
function precSousSalves(largages, salves){
  return `${precNombre(largages, "prec_larg_1", "prec_larg_n")} ${precNombre(salves, "prec_salve_1", "prec_salve_n")}`;
}
function precSousCanon(obus, rafales, rafalesAuBut){
  return `${precNombre(obus, "prec_obus_1", "prec_obus_n")} ${precNombre(rafales, "prec_raf_1", "prec_raf_n")} · ${precNombre(rafalesAuBut, "prec_rafbut_1", "prec_rafbut_n")}`;
}
// Le nom court : une parenthèse finale en moins (la désignation OTAN) ; deux armes d'un même cadre qui auraient
// le même nom court gardent toutes deux leur nom entier.
// Lot « Les référentiels » : une arme qui a un libellé s'affiche sous ce libellé (la clé brute au survol) ;
// seules les armes sans libellé suivent la règle du nom court.
function precNomsAffiches(noms){
  const court = nom => nom.replace(/\s*\([^()]*\)\s*$/, "");
  const distincts = [...new Set(noms)];
  const sans = distincts.filter(nom => !libellePour(LIBELLES.armes, nom));
  const compte = new Map();
  sans.forEach(nom => compte.set(court(nom), (compte.get(court(nom)) || 0) + 1));
  const affiches = new Map();
  distincts.forEach(nom => affiches.set(nom, libellePour(LIBELLES.armes, nom) || (compte.get(court(nom)) > 1 ? nom : court(nom))));
  return affiches;
}
// Le titre (clé brute au survol) d'une ligne d'arme dont le libellé diffère de la clé.
function precTitreArme(cle){
  return libArme(cle) !== cle ? ` title="${escapeAttr(cle)}"` : "";
}
// Une ligne en rapport (salves, canon) : nom · jauge · au but/total · pourcentage ; total nul → « — », jauge vide.
// Dessous, la ligne d'explication.
function precLigneRapportHtml(nom, affiche, auBut, total, explication){
  const p = total ? Math.round(100 * auBut / total) : null;
  return `<div class="wpn" title="${escapeAttr(nom)}"><span class="wn">${escapeHtml(affiche)}</span><span class="tk"><i style="width:${p == null ? 0 : p}%"></i></span><span class="wv">${auBut}/${total}</span><span class="wp">${p == null ? "—" : `${p} %`}</span></div><div class="wx">${escapeHtml(explication)}</div>`;
}
// `lignes` : [{cle, html}] dans l'ordre des données ; un groupe par type présent, dans l'ordre de PREC_TYPES.
function precGroupesHtml(lignes){
  return PREC_TYPES.map(ty => {
    const siennes = lignes.filter(l => l.cle === ty.cle);
    return siennes.length
      ? `<div class="prec-grp"><div class="subsec">${escapeHtml(t(ty.cle))}</div>${siennes.map(l => l.html).join("")}</div>`
      : "";
  }).join("");
}
// Sans famille ni canon (toutes les armes dans « Autres ») : ni groupe ni intertitre, le cadre d'avant.
function precSansTypes(lignes){
  return lignes.every(l => l.cle === "prec_cat_autres");
}

function precisionPanelHtml(f){
  // Clé réelle du dict stats = `shots_by_weapon` (cf. engine.py
  // _compute_flight_stats + checkpoint §3.2/invariant, déjà consommée par
  // totalShots() côté roster) -- le brief l'évoque en langage courant
  // ("precision_by_weapon") mais ⓐ ce n'est pas dans le périmètre autorisé
  // de retouche moteur (Volet A.1/A.2 seulement) ⓑ renommer casserait
  // totalShots(). On réutilise donc la clé existante, écart signalé.
  const sw = (f.stats && f.stats.shots_by_weapon) || {};
  // Lot « L'écran de la précision » : le canon et la famille des armes.
  const cw = (f.stats && f.stats.cannon_by_weapon) || {};
  const familles = (f.stats && f.stats.weapon_families) || {};
  const weapons = Object.keys(sw);
  const canons = Object.keys(cw);
  // Lot « L'efficacité par arme sur l'écran Vol » : sous une arme (ou un canon) dont `f.efficacite` porte des cibles
  // touchées, la ligne du Dossier (`pilotesEfficaciteHtml`) ; sans `f.efficacite`, rien.
  const effArme = (w, forme) => pilotesEfficaciteHtml(((f.efficacite || {})[forme] || {})[w] || {});
  const ligneArme = (w, affiche, titre) => {
    const v = sw[w] || {};
    // Lot « L'écran de la précision » : une arme à sous-munitions se lit en salves au but sur salves.
    // Lot « Le Débrief : la précision des roquettes par salve » : une roquette (famille 33) aussi, mais elle dit
    // « roquettes tirées » et non « conteneurs largués ».
    if(v.salvos != null){
      const explication = familles[w] === 33
        ? `${precNombre(v.shots || 0, "prec_roq_1", "prec_roq_n")} ${precNombre(v.salvos, "prec_salve_1", "prec_salve_n")}`
        : precSousSalves(v.releases || 0, v.salvos);
      return precLigneRapportHtml(w, affiche, v.salvos_hit || 0, v.salvos, explication);
    }
    // §5.3 : deux formes de shots_by_weapon -- {releases} seul (bombes/
    // roquettes non guidées, pas de .tk : rien à représenter) et
    // {shots,touched,precision} (arme guidée, .tk présent).
    if(v.releases != null){
      return `<div class="wpn"${titre}>
          <span class="wn">${escapeHtml(affiche)}</span>
          <span class="wv">${v.releases}</span>
          <span class="wp">${escapeHtml(t("flight_releases_word"))}</span>
        </div>`;
    }
    const pct = v.precision!=null ? Math.round(v.precision*100) : 0;
    const touched = v.touched!=null ? v.touched : 0;
    const shots = v.shots!=null ? v.shots : 0;
    return `<div class="wpn"${titre}>
        <span class="wn">${escapeHtml(affiche)}</span>
        <span class="tk"><i style="width:${pct}%"></i></span>
        <span class="wv">${touched}/${shots}</span>
        <span class="wp">${pct} %</span>
      </div>`;
  };
  let rowsHtml;
  if(weapons.length === 0 && canons.length === 0){
    rowsHtml = `<div class="note">${escapeHtml(t("flight_precision_empty"))}</div>`;
  } else {
    const types = weapons.map(w => ({w, cle: precTypeCle(familles[w])}));
    if(canons.length === 0 && precSansTypes(types)){
      // Sans famille ni canon : le cadre du v1.0028, noms entiers.
      rowsHtml = weapons.map(w => ligneArme(w, libArme(w), precTitreArme(w)) + effArme(w, "precision")).join("");
    } else {
      const affiches = precNomsAffiches(weapons.concat(canons));
      const lignes = types.map(({w, cle}) => ({cle, html: ligneArme(w, affiches.get(w), ` title="${escapeAttr(w)}"`) + effArme(w, "precision")}))
        .concat(canons.map(c => {
          const v = cw[c] || {};
          return {cle: "prec_cat_canon", html: precLigneRapportHtml(c, affiches.get(c), v.rounds_hit || 0, v.rounds || 0,
            precSousCanon(v.rounds || 0, v.bursts || 0, v.bursts_hit || 0)) + effArme(c, "canon")};
        }));
      rowsHtml = precGroupesHtml(lignes);
    }
  }
  return `<div class="framed">
    <div class="sec ink">${aircraftSilhouetteHtml(f.aircraft_type)}${escapeHtml(t("flight_precision_title"))}</div>
    ${rowsHtml}
  </div>`;
}

/* ---------- Menaces subies ----------
   Écart signalé (VOLET C) : la maquette affiche "{unité} · {catégorie}"
   -- la catégorie (référentiel `categorize`) n'est calculée que côté
   serveur et n'est pas exposée sur `threat_log` (hors périmètre autorisé
   d'ajouter un champ moteur pour ce lot). Remplacé par l'arme (donnée
   réellement disponible), cohérent avec le format déjà utilisé dans la
   timeline pour les mêmes entrées. */

function flightKillsPanelHtml(f){
  // Lot « Le bilan du pilote » -- mêmes barres que le bilan de session
  // (.bcat, mobilier inchangé), source = l'agrégat serveur du vol
  // (`kills_by_category`, posé par `_bilan_des_vols` dans api.py, le calcul
  // même du bilan de session). Le panneau
  // ne s'affiche pas quand le vol n'a rien détruit : un cadre vide ne dit
  // rien que la ligne « Abattages » du résumé ne dise déjà.
  const groups = f.kills_by_category || [];
  const frat = f.n_fratricides || 0;
  if(!groups.length && !frat) return "";
  const maxCount = groups.length ? groups[0].count : 0;
  const rows = groups.map(g=>{
    const width = maxCount>0 ? Math.round((g.count/maxCount)*100) : 0;
    return `<div class="bcat"><span class="cic ${CATEGORY_ICON[g.category] || "target-inconnu"}"></span><span class="c">${escapeHtml(catLabel(g.category))}</span><span class="tk ink"><i style="width:${width}%"></i></span><span class="v">${g.count}</span></div>`;
  }).join("");
  const total = f.n_kills_validated != null ? f.n_kills_validated : groups.reduce((n,g)=> n+g.count, 0);
  const motFrat = t(frat > 1 ? "flight_kills_frat" : "flight_kills_frat_un");
  const ligneFrat = frat ? `<p class="frat">${frat} ${escapeHtml(motFrat)}</p>` : "";
  return `<div class="framed">
    <div class="sec ink">${escapeHtml(t("flight_kills_title"))}<b class="tot">${escapeHtml(String(total))}</b></div>
    ${rows}${ligneFrat}
  </div>`;
}

function threatPanelHtml(f){
  const groups = aggregateThreatLog(f.stats && f.stats.threat_log);
  let bodyHtml = "";
  if(groups.length > 0){
    bodyHtml = `<div class="list">` + groups.map(g=>{
      const sevCls = graviteSevClass(g.gravite);
      // §5.1 : densité d'encre, pas de couleur -- visé -> .sev.a, touché
      // -> .sev.h, abattu -> .sev.d (correspondance brief §5.1).
      const sevChar = sevCls==="aimed" ? "am" : (sevCls==="hit" ? "ht" : "dn");
      const label = escapeHtml(graviteLabel(g.gravite));
      const src = g.initiator_unit_type ? libTypeHtml(g.initiator_unit_type) : "—";
      const wpnPart = g.weapon ? ` · ${libArmeHtml(g.weapon)}` : "";
      const countPart = g.count>1 ? ` (×${g.count})` : "";
      return `<div class="li">
        <span class="d">${horodatageHtml(flightRefTime(), g.t)}</span>
        <span class="t2">${src}${wpnPart}${countPart}</span>
        <span class="sev ${sevChar}">${label}</span>
      </div>`;
    }).join("") + `</div>`;
  }
  // Lot « Le Débrief : quatre défauts » : la note passe par l'i18n (texte inchangé).
  const noteHtml = groups.length === 0
    ? t("flight_threats_none_note")
    : "";
  // Lot 1.5b §13, corrigé par ARBITRAGE_LOT_1_5B_Conflit_P19.md §3.2 : le
  // rendu .foot inconditionnel du brief d'origine produisait une .note vide
  // à côté de l'AQAP dès qu'il y avait des menaces -- annulé. Conditionnalité
  // d'origine de la note "Aucun impact subi" rétablie (texte/condition
  // inchangés), sortie de .foot, rendue dans le corps du panneau. Un second
  // .foot, inconditionnel celui-là, ferme l'écran avec la note §1.10
  // (rappel non-comparaison) puis l'AQAP, extraits de la maquette (écran I).
  return `<div class="framed">
    <div class="sec ink">${aircraftSilhouetteHtml(f.aircraft_type)}${escapeHtml(t("flight_threats_title"))}</div>
    ${bodyHtml}
    ${noteHtml ? `<div class="note">${noteHtml}</div>` : ""}
    <div class="foot">
      <div class="aqap ink"><b>NATO STANDARD</b><br>AQAP-2110 · ÉD. 4</div>
    </div>
  </div>`;
}

/* ---------- Assemblage complet ---------- */

// Lot « Les heures de jour et de nuit » (v1.0068, R13) : l'étiquette de la
// période, à côté de la durée -- un bouton (un clic bascule) pour qui peut
// corriger, une simple étiquette sinon ; rien quand le vol n'a pas de période.
function periodeEtiquetteHtml(f){
  if(!f.periode) return "";
  const nom = p => t(p === "nuit" ? "flight_periode_nuit" : "flight_periode_jour");
  const libelle = nom(f.periode) + (f.periode_corrigee ? ` · ${t("flight_periode_corrigee")}` : "");
  if(!f.periode_modifiable) return `<span class="jn-tag">${escapeHtml(libelle)}</span>`;
  const autre = f.periode === "nuit" ? "jour" : "nuit";
  const titre = t("flight_periode_corriger").replace("{p}", nom(autre));
  return `<button type="button" class="jn-tag" data-periode-basculer="${autre}" title="${escapeHtml(titre)}">${escapeHtml(libelle)}</button>`;
}

function flightViewHtml(f){
  const stats = f.stats || {};
  const killsN = (stats.kills||[]).length;
  const morts = (stats.crashed || stats.pilot_dead) ? 1 : 0;
  const bilan = killsN - morts;
  const bilanText = bilan>0 ? `+${bilan}` : String(bilan);
  const issue = flightIssue(stats);
  const altFmt = fmtAltM(stats.alt_max);
  const altHtml = altFmt!=null ? `${altFmt} <small>m</small>` : "—";

  // .kick = titre de mission · date (brief §4). Session déjà chargée par
  // ④ (renderFlight() la résout de même) ; pas de repli inventé -- pas de
  // campagne au modèle (dette 20), segment omis si la session n'est pas
  // encore là plutôt que fabriqué.
  const session = (CURRENT_SESSION && CURRENT_SESSION.id === CURRENT_SESSION_ID) ? CURRENT_SESSION : null;
  const kickHtml = session
    ? `${escapeHtml(session.display_title)} · ${escapeHtml(fmtSessionDateInline(session.mission_date))}`
    : "";

  // Écart signalé E1 (AVENANT_1 §G) : .etat n'a qu'un seul contour
  // générique en encre de tampon -- pas de variante par issue (RTB/KIA/
  // Éjection) comme l'ancien .issue.rtb/.kia/.eject (couleur + glyphe).
  // Porté tel quel, non fabriqué de variantes .etat.rtb/.kia/.eject.
  //
  // AVENANT 2 §B : .idbar a exactement DEUX enfants (le mobilier est un
  // flex à 2 items, aucun flex-wrap déclaré -- avec un 3e item la rangée
  // ne peut plus se replier). .etat est nichée en fin de .callsign, EN
  // LIGNE, pas comme item flex séparé -- c'est ce que .etat{display:
  // inline-block} suppose. Cause du débord Porte 8 signalé puis corrigé.
  // Lot 1.5 §3 — tampon "Incomplet" : lieu principal, dans le bandeau
  // d'identité, à côté de .etat (jamais en travers du contenu).
  const stampHtml = flightStampHtml(f);

  return `<div class="idbar">
    <div>
      <div class="kick">${kickHtml}</div>
      <div class="callsign ink worn">${f.pilote_profile_id ? `<a href="#" class="vol-pilote" data-ouvre-membre="${escapeAttr(String(f.pilote_profile_id))}">${escapeHtml(flightHeaderName(f))}</a>` : escapeHtml(flightHeaderName(f))}<span class="etat ${issue.key}">${escapeHtml(issue.label)}</span>${stampHtml}${natureStampHtml(CURRENT_SESSION)}</div>
    </div>
    <div class="meta">${flightMetaHtml(f)}</div>
  </div>
  <div class="rule2 ink"></div>
  ${slipHtml(f)}

  <div class="framed" data-decor="summary">
    <div class="sec ink">${aircraftSilhouetteHtml(f.aircraft_type)}${escapeHtml(t("flight_summary_title"))}</div>
    <div class="stats${f.periode ? " jn-large" : ""}">
      <div class="stat"><div class="v">${killsN}</div><div class="l">${escapeHtml(t("flight_stat_kills"))}</div></div>
      <div class="stat${f.periode ? " jn-vol" : ""}"><div class="v">${escapeHtml(fmtDuree(stats.flight_time_s))}${periodeEtiquetteHtml(f)}</div><div class="l">${escapeHtml(t("flight_stat_time"))}</div></div>
      <div class="stat"><div class="v">${altHtml}</div><div class="l">${escapeHtml(t("flight_stat_altmax"))}</div></div>
      <div class="stat"><div class="v">${escapeHtml(bilanText)}</div><div class="l">${escapeHtml(t("flight_stat_bilan"))}</div></div>
    </div>
    ${decorumPhotoHtml(f, "flight", "rr-photo")}
    <span class="rr-crest-compact" id="flight-crest-compact" aria-hidden="true"></span>
  </div>

  <div class="framed" data-decor="timeline">
    <div class="sec ink">${aircraftSilhouetteHtml(f.aircraft_type)}${escapeHtml(t("flight_timeline_title"))}</div>
    ${flightTimelineHtml(f)}
    ${decorumPhotoHtml(f, "flight", "rr-photo-bas")}
  </div>

  <div class="duo">
    <div>${precisionPanelHtml(f)}${flightKillsPanelHtml(f)}</div>
    ${threatPanelHtml(f)}
  </div>`;
}

// Lot « Le nom qu'on retient » v0.9917 -- bordereau d'identification
// (brief §1/§6), MÉCANISME UNIQUE qui remplace l'ancien "Identifier ce
// vol"/"Annuler l'identification" (v0.9913/v0.9915) : le champ de saisie
// libre a disparu, il ne reste qu'un geste, désigner un membre. Admin
// uniquement (ME.is_admin === true, miroir exact des gardes serveur des
// quatre routes concernées). S'insère entre le bandeau d'identité et la
// Synthèse du vol, comme l'ancien bloc (flightViewHtml, ligne ci-dessus).
//
// Trois situations (brief §6), UNE SEULE à la fois :
//   1. non rattaché (!f.pilote_profile_id)            -> slipEditPanelHtml
//   2/3. rattaché, vue "faite" par défaut              -> slipDoneHtml
//        "Corriger" bascule vers 2. via identifyFlightOpen
//
// Origine affichée en "done" (brief §6, tableau) : alias / manuel / le
// reste (nom_acmi, acmi_type_unique, under_control, replication, declare)
// regroupé sous "le moteur" -- la maquette ne distingue que ces trois
// termes, jamais par identity_source brut.
function slipOrigin(f){
  if(f.identity_source === "alias") return "alias";
  if(f.identity_source === "manuel") return "manual";
  return "engine";
}

// Résout le nom d'affichage d'un membre depuis l'annuaire (DEBRIEF_MEMBERS,
// cache chargé par ensureDebriefMembersLoaded()) -- jamais depuis le
// segment du callsign : un vol "manuel" peut porter un indicatif qui ne
// correspond plus au membre réellement désigné (brief §6, l'automatique
// n'arbitre pas ce cas).
function slipMemberName(profileId){
  if(!profileId || !DEBRIEF_MEMBERS) return "";
  const m = DEBRIEF_MEMBERS.find(x=> x.id === profileId);
  return m ? m.name : "";
}

// Sélection EFFECTIVE du <select> : ce que l'utilisateur a explicitement
// choisi (slipSelectedProfileId, y compris "" = vidé) prime toujours ;
// sinon, en mode "Corriger" (vol déjà rattaché), la sélection par défaut
// est le membre actuel -- jamais pour un vol non rattaché (pas de défaut
// à proposer).
function slipEffectiveSelection(f, isAttached){
  if(slipSelectedProfileId !== null) return slipSelectedProfileId;
  return (isAttached && f.pilote_profile_id) ? f.pilote_profile_id : "";
}

// <select> groupé par escadrille (brief §6), groupe "Sans escadrille" en
// dernier pour les Free Agents -- ordre alphabétique des désignations,
// membres dans l'ordre déjà trié par le serveur (global_name, username).
function slipMemberSelectHtml(members, selectedId){
  const bySquadron = new Map();
  members.forEach(m=>{
    const key = m.squadron || "";
    if(!bySquadron.has(key)) bySquadron.set(key, []);
    bySquadron.get(key).push(m);
  });
  const squadronNames = Array.from(bySquadron.keys()).filter(k=> k!=="").sort((a,b)=> a.localeCompare(b));
  const optionHtml = m => `<option value="${escapeAttr(m.id)}"${selectedId===m.id ? " selected" : ""}>${escapeHtml(m.name)}</option>`;
  let groupsHtml = squadronNames.map(sq =>
    `<optgroup label="${escapeAttr(sq)}">${bySquadron.get(sq).map(optionHtml).join("")}</optgroup>`
  ).join("");
  if(bySquadron.has("")){
    groupsHtml += `<optgroup label="${escapeAttr(t("slip_select_no_squadron"))}">${bySquadron.get("").map(optionHtml).join("")}</optgroup>`;
  }
  return `<select id="slip-member-select">
    <option value="">${escapeHtml(t("slip_select_placeholder"))}</option>
    ${groupsHtml}
  </select>`;
}

// Situation 1 (non rattaché, toujours affichée telle quelle) ET mode
// "Corriger" (2/3 -> édition). Mémo affiché seulement si un segment ET une
// sélection existent tous les deux (rien à annoncer sinon) -- shortCallsign()
// est la fonction MIROIR de `_extract_name_segment()` (engine.py), jamais
// réimplémentée ici (cf. son commentaire, styles.css:3442).
function slipEditPanelHtml(f, isAttached){
  const selection = slipEffectiveSelection(f, isAttached);
  const selectHtml = DEBRIEF_MEMBERS
    ? slipMemberSelectHtml(DEBRIEF_MEMBERS, selection)
    : `<select id="slip-member-select" disabled><option>…</option></select>`;
  const segment = shortCallsign(f.pilot_callsign || "");
  const selectedName = selection ? slipMemberName(selection) : "";
  const showMemo = !!(segment && selection);
  const memoHtml = showMemo
    ? `<div class="memo">
        <span class="ico">✍</span>
        <p>${escapeHtml(t("slip_memo").replace("{segment}", segment).replace("{who}", selectedName))}</p>
      </div>`
    : "";
  return `<div class="slip">
    <div class="hd"><span class="t">${escapeHtml(t("slip_hd_title"))}</span><span class="who">${escapeHtml(t("slip_hd_who"))}</span></div>
    <div class="field">
      <label>${escapeHtml(t("slip_select_label"))}</label>
      ${selectHtml}
    </div>
    ${memoHtml}
    <div class="acts">
      <button type="button" class="btn btn-sm" data-slip-cancel>${escapeHtml(t("slip_cancel"))}</button>
      <button type="button" class="btn btn-sm btn-accent" data-slip-attach>${escapeHtml(t("slip_attach"))}</button>
    </div>
  </div>`;
}

// Situations 2/3 (rattaché, vue "faite" par défaut). "Oublier ce nom"
// seulement pour l'origine "alias" (brief §6, tableau -- le moteur/la main
// n'ont rien à oublier, pas de ligne `profile_dcs_alias` derrière eux).
function slipDoneHtml(f){
  const origin = slipOrigin(f);
  const who = slipMemberName(f.pilote_profile_id);
  const callsign = f.pilot_callsign || "";
  const doneText = origin === "alias"
    ? t("slip_done_alias").replace("{who}", who).replace("{callsign}", callsign)
    : origin === "manual"
      ? t("slip_done_manual").replace("{who}", who)
      : t("slip_done_engine").replace("{who}", who).replace("{callsign}", callsign);
  const forgetHtml = origin === "alias"
    ? `<button type="button" class="btn btn-xs" data-slip-forget>${escapeHtml(t("slip_forget"))}</button>`
    : "";
  return `<div class="slip">
    <div class="hd"><span class="t">${escapeHtml(t("slip_hd_title"))}</span><span class="who">${escapeHtml(t("slip_hd_who"))}</span></div>
    <div class="done">
      <p>${escapeHtml(doneText)}</p>
      <button type="button" class="btn btn-xs" data-slip-correct>${escapeHtml(t("slip_correct"))}</button>
      <button type="button" class="btn btn-xs btn-quiet" data-slip-detach>${escapeHtml(t("slip_detach"))}</button>
      ${forgetHtml}
    </div>
  </div>`;
}

function slipHtml(f){
  if(!(ME && ME.is_admin === true)) return "";
  const isAttached = !!f.pilote_profile_id;
  if(isAttached && !identifyFlightOpen) return slipDoneHtml(f);
  return slipEditPanelHtml(f, isAttached);
}

function wireFlightMount(){
  const mount = $("#flight-mount");
  if(!mount) return;
  mount.addEventListener("click", (e)=>{
    const retryBtn = e.target.closest("[data-flight-retry]");
    if(retryBtn){ ensureFlightLoaded(CURRENT_FLIGHT_ID); return; }
    // "Corriger" (situations 2/3) : bascule vers le panneau d'édition,
    // présélectionné sur le membre actuel (slipEffectiveSelection()).
    const slipCorrect = e.target.closest("[data-slip-correct]");
    if(slipCorrect){ identifyFlightOpen = true; slipSelectedProfileId = null; renderFlight(); return; }
    // "Annuler" : ferme le mode "Corriger" s'il était ouvert (retour à la
    // vue "faite") ; sinon (situation 1, pas de mode à fermer) vide
    // simplement la sélection en cours -- même bouton, deux contextes.
    const slipCancel = e.target.closest("[data-slip-cancel]");
    if(slipCancel){
      if(identifyFlightOpen){ identifyFlightOpen = false; slipSelectedProfileId = null; }
      else { slipSelectedProfileId = ""; }
      renderFlight();
      return;
    }
    // Lot « Les heures de jour et de nuit » (R14) : un clic sur l'étiquette bascule la période.
    const periodeBtn = e.target.closest("[data-periode-basculer]");
    if(periodeBtn){ basculerPeriodeVol(periodeBtn.dataset.periodeBasculer); return; }
    const slipAttach = e.target.closest("[data-slip-attach]");
    if(slipAttach){ saveSlipAttach(); return; }
    const slipDetach = e.target.closest("[data-slip-detach]");
    if(slipDetach){ slipDetachFlight(slipDetach); return; }
    const slipForget = e.target.closest("[data-slip-forget]");
    if(slipForget){ slipForgetAlias(slipForget); return; }
  });
  // Même patron délégué que missionsFilters.sim (wireMissionsMount) : pas
  // de patch local, re-rendu complet -- la sélection vit dans
  // slipSelectedProfileId, relue par slipEffectiveSelection() au rendu.
  mount.addEventListener("change", (e)=>{
    if(e.target.id === "slip-member-select"){
      slipSelectedProfileId = e.target.value || "";
      renderFlight();
    }
  });
}

// Lot « Les heures de jour et de nuit » (R14) : PATCH .../periode avec la valeur
// voulue, puis rechargement forcé du vol et de la session (comme saveSlipAttach) ;
// rien ne se calcule côté client, aucun toast de réussite.
async function basculerPeriodeVol(periode){
  try {
    await apiFetch(`/api/debrief/sessions/${CURRENT_SESSION_ID}/flights/${CURRENT_FLIGHT_ID}/periode`, {
      method:"PATCH", headers:{"Content-Type":"application/json"}, body: JSON.stringify({periode})
    });
    flightDetailLoadState = "idle";
    sessionDetailLoadState = "idle";
    await ensureFlightLoaded(CURRENT_FLIGHT_ID);
    await ensureSessionLoaded(CURRENT_SESSION_ID);
  } catch(e){
    showToast(e.message || t("flight_periode_fail"), "erreur");
  }
}

// "Rattacher"/"Corriger" -- POST .../identify avec pilote_profile_id
// (aucune saisie libre, brief §1). Même patron que les autres actions
// d'écriture de cette vue : rechargement forcé fiche + session (l'identité
// et ses effets -- roster, groupement -- sont recalculés côté serveur, on
// ne les devine jamais côté client).
async function saveSlipAttach(){
  const f = CURRENT_FLIGHT;
  if(!f) return;
  const selection = slipEffectiveSelection(f, !!f.pilote_profile_id);
  if(!selection){
    showToast(t("slip_attach_error"), "erreur");
    return;
  }
  try {
    await apiFetch(`/api/debrief/sessions/${CURRENT_SESSION_ID}/flights/${CURRENT_FLIGHT_ID}/identify`, {
      method:"POST", headers:{"Content-Type":"application/json"}, body: JSON.stringify({pilote_profile_id: selection})
    });
    identifyFlightOpen = false;
    slipSelectedProfileId = null;
    showToast(t("slip_attach_done"));
    flightDetailLoadState = "idle";
    sessionDetailLoadState = "idle";
    await ensureFlightLoaded(CURRENT_FLIGHT_ID);
    await ensureSessionLoaded(CURRENT_SESSION_ID);
  } catch(e){
    showToast(e.message || t("slip_attach_fail"), "erreur");
  }
}

// "Détacher" -- DELETE .../identify, sémantique élargie v0.9917 (brief §5) :
// détachement DÉFINITIF, quelle que soit l'origine. Confirmation explicite
// (brief §6 : "dit ce qui va se passer").
// Lot « La charte commune, au Débrief » (v1.0080) : la note commune sous le geste remplace la boîte grise.
async function slipDetachFlight(btn){
  const ok = await rrConfirmer({
    ancre: btn.closest(".done"), geste: btn,
    titre: t("slip_detach_titre"), texte: escapeHtml(t("slip_detach_texte")), libelle: t("slip_detach"), danger: true,
    action: async ()=>{
      showToast(t("slip_detach_running"));
      try {
        await apiFetch(`/api/debrief/sessions/${CURRENT_SESSION_ID}/flights/${CURRENT_FLIGHT_ID}/identify`, {
          method:"DELETE"
        });
      } catch(e){ throw new Error(e.message || t("slip_detach_fail")); }
    }
  });
  if(!ok) return;
  try {
    identifyFlightOpen = false;
    slipSelectedProfileId = null;
    showToast(t("slip_detach_done"));
    flightDetailLoadState = "idle";
    sessionDetailLoadState = "idle";
    await ensureFlightLoaded(CURRENT_FLIGHT_ID);
    await ensureSessionLoaded(CURRENT_SESSION_ID);
  } catch(e){
    showToast(e.message || t("slip_detach_fail"), "erreur");
  }
}

// "Oublier ce nom" -- DELETE .../alias (route neuve, brief §5). Ne
// concerne que l'origine "alias" (seul cas où slipDoneHtml pose le
// bouton).
async function slipForgetAlias(btn){
  const ok = await rrConfirmer({
    ancre: btn.closest(".done"), geste: btn,
    titre: t("slip_forget_titre"), texte: escapeHtml(t("slip_forget_texte")), libelle: t("slip_forget"), danger: true,
    action: async ()=>{
      showToast(t("slip_forget_running"));
      try {
        await apiFetch(`/api/debrief/sessions/${CURRENT_SESSION_ID}/flights/${CURRENT_FLIGHT_ID}/alias`, {
          method:"DELETE"
        });
      } catch(e){ throw new Error(e.message || t("slip_forget_fail")); }
    }
  });
  if(!ok) return;
  try {
    identifyFlightOpen = false;
    slipSelectedProfileId = null;
    showToast(t("slip_forget_done"));
    flightDetailLoadState = "idle";
    sessionDetailLoadState = "idle";
    await ensureFlightLoaded(CURRENT_FLIGHT_ID);
    await ensureSessionLoaded(CURRENT_SESSION_ID);
  } catch(e){
    showToast(e.message || t("slip_forget_fail"), "erreur");
  }
}

// Lot 2.1 §4.5 : PATCH non destructif, aucun effet de bord. `null` efface
// (repli sur l'embelli côté serveur) ; chaîne vide -> null côté client
// (le serveur refuse une chaîne vide en 422, cf. brief §4.5).
async function saveSessionEdit(){
  const nameInput = $("#session-edit-name-input");
  const noteInput = $("#session-edit-note-input");
  const campaignSelect = $("#session-edit-campaign-select");
  if(!nameInput || !noteInput) return;
  const nameVal = nameInput.value.trim();
  const noteVal = noteInput.value.trim();
  if(nameVal.length > 80 || noteVal.length > 2000){
    showToast(t("error_field_too_long"), "erreur");
    return;
  }
  const body = {
    display_name: nameVal ? nameVal : null,
    wing_note: noteVal ? noteVal : null,
  };
  // Lot 2.3 §4.8b/§9 : `campaign_id` envoyé UNIQUEMENT si la sélection a
  // réellement changé par rapport à sa valeur initiale (`data-initial`,
  // posée au rendu du panneau). Le défaut nommé au §9 du brief est
  // exactement celui déjà corrigé pour le nom -- un champ non touché ne
  // doit jamais envoyer `null` et détacher une campagne en silence.
  if(campaignSelect){
    const initial = campaignSelect.dataset.initial || "";
    const current = campaignSelect.value || "";
    if(current !== initial){
      body.campaign_id = current ? current : null;
    }
  }
  // Lot « Mission ou training » : `nature` envoyée UNIQUEMENT si la sélection a
  // changé par rapport à `data-initial` -- le patron de `campaign_id` ci-dessus.
  const natureSelect = $("#session-edit-nature-select");
  if(natureSelect){
    const initialNature = natureSelect.dataset.initial || "mission";
    if(natureSelect.value !== initialNature){
      body.nature = natureSelect.value;
    }
  }
  try {
    const updated = await apiFetch(`/api/debrief/sessions/${CURRENT_SESSION_ID}`, {
      method:"PATCH", headers:{"Content-Type":"application/json"}, body: JSON.stringify(body)
    });
    if(CURRENT_SESSION && CURRENT_SESSION.id === CURRENT_SESSION_ID){
      CURRENT_SESSION.display_name = updated.display_name;
      CURRENT_SESSION.wing_note = updated.wing_note;
      CURRENT_SESSION.display_title = updated.display_title;
      CURRENT_SESSION.campaign = updated.campaign;
      CURRENT_SESSION.nature = updated.nature;
    }
    // Pochette Missions : mise à jour locale du cache déjà chargé, pas de
    // re-fetch réseau (le résumé liste ne porte que display_title/campaign).
    const listed = (DEBRIEF_SESSIONS||[]).find(x=> x.id === CURRENT_SESSION_ID);
    if(listed){
      listed.display_title = updated.display_title;
      listed.campaign = updated.campaign;
      listed.nature = updated.nature;
    }
    sessionEditOpen = false;
    showToast(t("session_edit_saved"));
    renderSession();
  } catch(e){
    showToast(e.message || t("error_generic"), "erreur");
  }
}

// Lot « Recalcul de session » v0.9914 -- recalcule intégralement la session
// depuis ses fichiers bruts (moteur `recompute_session`, idempotent). Action
// lourde (reparse ACMI de plusieurs dizaines de Mo) : confirmation requise.
// Rechargement forcé après succès -- ensureSessionLoaded court-circuite sur
// id inchangé + état "ready" (cf. saveIdentifyFlight, même patron), on ne
// devine jamais l'état recalculé côté client, on le relit.
// Lot « La charte commune, au Débrief » (v1.0080) : la note commune sous le geste (`rrConfirmer`) remplace la boîte
// grise ; elle désactive elle-même ses boutons pendant l'appel, le bouton du geste n'est donc plus désactivé ici.
async function recomputeSession(btn){
  const ok = await rrConfirmer({
    ancre: btn.closest(".idbar"), geste: btn,
    titre: t("recompute_titre"), texte: escapeHtml(t("recompute_texte")), libelle: t("recompute_go"),
    action: async ()=>{
      showToast(t("recompute_running"));
      try {
        await apiFetch(`/api/debrief/sessions/${CURRENT_SESSION_ID}/recompute`, {method:"POST"});
      } catch(e){ throw new Error(t("recompute_error")); }
    }
  });
  if(!ok) return;
  showToast(t("recompute_done"));
  sessionDetailLoadState = "idle";
  await ensureSessionLoaded(CURRENT_SESSION_ID);
}

// Lot Fraîcheur v0.9939 (brief §7/§8 F3) : « Tout recalculer » -- POST
// /sessions/recompute-stale (admin only, même route pour la tâche de fond
// du serveur, cf. app/main.py). Même patron que recomputeSession()
// ci-dessus : confirmation obligatoire, bouton désactivé pendant l'appel,
// jamais d'état recalculé deviné côté client -- la liste Missions est
// invalidée (missionsLoadState="idle", rechargée à la prochaine visite) et
// la session courante est relue pour de vrai, elle peut avoir changé.
async function recomputeAllStale(btn){
  const n = (CURRENT_SESSION && CURRENT_SESSION.stale_count) || 0;
  const texte = escapeHtml(t("recompute_all_texte").split("{n}").join(String(n)).split("{s}").join(n > 1 ? "s" : ""));
  let data;
  const ok = await rrConfirmer({
    ancre: btn.closest(".idbar"), geste: btn,
    titre: t("recompute_all_titre"), texte, libelle: t("recompute_all_go"),
    action: async ()=>{
      showToast(t("recompute_running"));
      try {
        data = await apiFetch("/api/debrief/sessions/recompute-stale", {method:"POST"});
      } catch(e){ throw new Error(t("recompute_error")); }
    }
  });
  if(!ok) return;
  showToast(t("recompute_all_toast").replace("{n}", data.recomputed));
  missionsLoadState = "idle";
  sessionDetailLoadState = "idle";
  await ensureSessionLoaded(CURRENT_SESSION_ID);
}

function wireSessionMount(){
  // Délégation : le contenu de #session-mount est régénéré à chaque rendu
  // (mêmes principes que #missions-mount, cf. wireMissionsMount) -- les
  // lignes de roster et le bouton rapport sont donc câblés ici, jamais en
  // querySelectorAll direct à l'init (qui raterait tout contenu dynamique).
  const mount = $("#session-mount");
  if(mount){
    mount.addEventListener("click", (e)=>{
      const retryBtn = e.target.closest("[data-session-retry]");
      if(retryBtn){ ensureSessionLoaded(CURRENT_SESSION_ID); return; }
      const reportBtn = e.target.closest("[data-open-report]");
      if(reportBtn){ openModalReport(); return; }
      // Lot 2.1 §4.8b : bascule/annulation/sauvegarde du bloc d'édition
      // nom/note -- vérifiées avant data-open-flight (aucune collision de
      // sélecteur possible, mais même discipline que groupToggle ci-dessous).
      const editToggle = e.target.closest("[data-toggle-session-edit]");
      if(editToggle){
        sessionEditOpen = !sessionEditOpen;
        // Lot « Le rattachement des dépôts » : la fusion repart de « aucune » ; la liste des missions se charge
        // si elle ne l'est pas, puis le panneau se redessine.
        sessionMergeChoice = "";
        sessionMergeConfirm = false;
        if(sessionEditOpen && (missionsLoadState !== "ready" || !DEBRIEF_SESSIONS)){
          ensureAutresMissions().then(renderSession);
        }
        // Lot 2.3 §4.8b : chargée paresseusement, une seule fois -- si pas
        // encore en cache, on rend d'abord sans le sélecteur peuplé (option
        // "Aucune" seule) puis on re-rend dès la réponse.
        if(sessionEditOpen && DEBRIEF_CAMPAIGNS === null){
          ensureCampaignsLoaded(CURRENT_SESSION ? CURRENT_SESSION.sim : "dcs").then(renderSession);
        }
        renderSession();
        return;
      }
      const editCancel = e.target.closest("[data-cancel-session-edit]");
      if(editCancel){ sessionEditOpen = false; renderSession(); return; }
      const editSave = e.target.closest("[data-save-session-edit]");
      if(editSave){ saveSessionEdit(); return; }
      const recomputeBtn = e.target.closest("[data-recompute-session]");
      if(recomputeBtn){ recomputeSession(recomputeBtn); return; }
      // Lot « Le rattachement des dépôts » : déplacer un fichier, fusionner deux missions.
      const moveBtn = e.target.closest("[data-move-upload]");
      if(moveBtn){
        const id = moveBtn.dataset.moveUpload;
        sessionMoveUploadId = (sessionMoveUploadId === id) ? null : id;
        if(sessionMoveUploadId && (missionsLoadState !== "ready" || !DEBRIEF_SESSIONS)){
          ensureAutresMissions().then(renderSession);
        }
        renderSession();
        return;
      }
      if(e.target.closest("[data-move-cancel]")){ sessionMoveUploadId = null; renderSession(); return; }
      const moveGo = e.target.closest("[data-move-go]");
      if(moveGo){ moveUploadGo(moveGo); return; }
      if(e.target.closest("[data-merge-cta]")){ if(sessionMergeChoice){ sessionMergeConfirm = true; renderMergeAct(); } return; }
      if(e.target.closest("[data-merge-cancel]")){ sessionMergeConfirm = false; renderMergeAct(); return; }
      const mergeGo = e.target.closest("[data-merge-go]");
      if(mergeGo){ mergeSessionsGo(mergeGo); return; }
      // Lot Fraîcheur v0.9939 (brief §8 F3) : vérifié AVANT data-recompute-
      // session ci-dessus impossible en pratique (sélecteurs disjoints),
      // même discipline que les autres boutons de .idacts.
      const recomputeAllBtn = e.target.closest("[data-recompute-all-stale]");
      if(recomputeAllBtn){ recomputeAllStale(recomputeAllBtn); return; }
      // Chgt 1 : dépli/repli d'un groupe roster -- vérifié AVANT
      // data-open-flight (les sous-lignes, elles, gardent le drill par vie).
      const groupToggle = e.target.closest("[data-group-toggle]");
      if(groupToggle){
        const key = groupToggle.dataset.groupToggle;
        if(rosterExpandedGroups.has(key)) rosterExpandedGroups.delete(key);
        else rosterExpandedGroups.add(key);
        renderSession();
        return;
      }
      const row = e.target.closest("[data-open-flight]");
      if(row){ openFlight(row.dataset.openFlight); return; }
    });
    // Lot « Mission ou training » : choisir une campagne remet la nature sur
    // Mission ; un éditeur peut ensuite la passer en Training.
    mount.addEventListener("change", (e)=>{
      // Lot « Le rattachement des dépôts » : choisir la mission à fusionner.
      if(e.target.id === "session-merge-select"){
        sessionMergeChoice = e.target.value;
        sessionMergeConfirm = false;
        renderMergeAct();
        return;
      }
      if(e.target.id === "session-edit-campaign-select" && e.target.value){
        const natureSel = $("#session-edit-nature-select");
        if(natureSel) natureSel.value = "mission";
      }
    });
    mount.addEventListener("keydown", (e)=>{
      if(e.key!=="Enter" && e.key!==" ") return;
      const groupToggle = e.target.closest("[data-group-toggle]");
      if(groupToggle){
        e.preventDefault();
        const key = groupToggle.dataset.groupToggle;
        if(rosterExpandedGroups.has(key)) rosterExpandedGroups.delete(key);
        else rosterExpandedGroups.add(key);
        renderSession();
      }
    });
  }
}

/* ================= Lot D2⑤ : modale Rapport de mission (#modal-report) =================
   Overlay DISTINCT (comme #modal-deposer) -- classes de shell partagées
   seulement. Récit + Brut horodaté générés depuis session.flights[].stats
   (kills/pertes/menaces), assemblage déterministe (brief §D, rappel §1.10 :
   jamais de classement/meilleur pilote/superlatif). Consomme CURRENT_SESSION
   déjà chargée (④) -- la modale n'est accessible que depuis l'écran Session. */

function reportFlightName(f){
  return f.identity_state === "anonyme" ? anonFlightLabel(f.aircraft_type) : shortCallsign(flightName(f));
}

function collectReportFacts(s){
  // Faits = kills validés + pertes (KIA) + menaces notables ("touché" --
  // "abattu" est délibérément exclu ici : il est déjà couvert par le fait
  // "perte" du même vol, l'inclure aussi comme menace narrerait deux fois
  // la même destruction). "visé" (raté) est exclu du récit/brut : bruit
  // volumineux, aucune valeur factuelle nouvelle (cf. §11.7 guide : ne pas
  // inventer de métrique, rester sur ce que le moteur produit d'utile).
  const flights = s.flights || [];
  const facts = [];
  flights.forEach(f=>{
    const stats = f.stats || {};
    const name = reportFlightName(f);
    (stats.kills||[]).forEach(k=>{
      const tgt = k.target_unit_type ? libType(k.target_unit_type) : "—";
      const arme = k.weapon ? libArme(k.weapon) : null;
      facts.push({
        t: k.t || 0, kind:"kill", hl:true,
        fr: arme ? `${name} détruit ${tgt} au ${arme}.` : `${name} détruit ${tgt}.`,
        en: arme ? `${name} destroyed ${tgt} with ${arme}.` : `${name} destroyed ${tgt}.`,
      });
    });
    if(flightIssue(stats).key === "kia"){
      const phaseHit = (stats.phases||[])
        .filter(p=> p.type==="crash" || p.type==="pilot dead")
        .sort((a,b)=> a.t - b.t)[0];
      const tt = phaseHit ? phaseHit.t : (f.t_end!=null ? f.t_end : 0);
      facts.push({
        t: tt, kind:"loss", dim:true,
        fr: stats.ejected ? `${name} perdu (éjection réussie).` : `${name} perdu.`,
        en: stats.ejected ? `${name} lost (successful ejection).` : `${name} lost.`,
      });
    }
    aggregateThreatLog(stats.threat_log).forEach(g=>{
      if(g.gravite !== "touché") return;
      const src = g.initiator_unit_type ? libType(g.initiator_unit_type) : "—";
      const arme = g.weapon ? libArme(g.weapon) : null;
      const suffix = g.count>1 ? ` (×${g.count})` : "";
      const baseFr = arme ? `${name} touché par ${src} au ${arme}` : `${name} touché par ${src}`;
      const baseEn = arme ? `${name} hit by ${src} with ${arme}` : `${name} hit by ${src}`;
      facts.push({
        t: g.t || 0, kind:"threat",
        fr: `${baseFr}${suffix}.`,
        en: `${baseEn}${suffix}.`,
      });
    });
  });
  facts.sort((a,b)=> (a.t||0) - (b.t||0));
  return facts;
}

function reportLineHtml(fact, ancre){
  const cls = "report-line" + (fact.hl?" hl":"");
  const txt = escapeHtml(currentLang==="fr" ? fact.fr : fact.en);
  const tCls = "t" + (fact.kind==="loss" ? " dead" : "");
  const textSpan = fact.dim ? `<span class="dim">${txt}</span>` : `<span>${txt}</span>`;
  return `<div class="${cls}"><span class="${tCls}">${horodatageHtml(ancre, fact.t)}</span>${textSpan}</div>`;
}

function reportRawHtml(s){
  // INCHANGÉ (Lot R2, brief §5 : "le Brut horodaté inchangé") -- toujours
  // l'assemblage mécanique, calculé côté client depuis les vols de la
  // session, comme avant ce lot.
  const facts = collectReportFacts(s);
  if(facts.length === 0){
    return `<p class="muted" style="font-size:.85rem">${escapeHtml(t("report_empty"))}</p>`;
  }
  return facts.map(fact => reportLineHtml(fact, s)).join("");
}

// Lot R2 §5 : le Récit n'est plus assemblé mécaniquement côté client
// (l'ancien reportNarrativeHtml -- avec ses lignes d'ouverture/bilan
// synthétiques -- est retiré, R78/R82 : la prose vient du modèle, figée en
// base par app/llm.py, servie par GET .../report). Un paragraphe par ligne
// non vide du texte reçu -- la mise en forme (retours à la ligne) reste
// celle produite par le modèle, jamais réinterprétée.
function reportRecitHtml(texte){
  return texte
    .split(/\n+/)
    .map(p=> p.trim())
    .filter(Boolean)
    .map(p=> `<p>${escapeHtml(p)}</p>`)
    .join("");
}

function reportNarrativeBodyHtml(){
  if(REPORT_DATA === null){
    return `<p class="muted" style="font-size:.85rem">${escapeHtml(t("report_loading"))}</p>`;
  }
  if(!REPORT_DATA.exists){
    return `<p class="muted" style="font-size:.85rem">${escapeHtml(t("report_not_generated"))}</p>`;
  }
  const texte = currentLang==="fr" ? REPORT_DATA.texte_fr : REPORT_DATA.texte_en;
  if(!texte){
    // R123 -- en anglais, tant que la traduction n'est pas là (ou a échoué),
    // on montre le français plutôt que rien, précédé d'une mention distincte
    // selon `redaction_en_cours` (champ existant, pas d'état neuf). Le cas
    // "texte_fr vide en langue FR" garde report_not_generated -- inchangé.
    if(currentLang==="en" && REPORT_DATA.texte_fr){
      const mentionKey = REPORT_DATA.redaction_en_cours
        ? "report_translation_pending"
        : "report_translation_unavailable";
      return `<p class="muted" style="font-size:.85rem">${escapeHtml(t(mentionKey))}</p>`
        + reportRecitHtml(REPORT_DATA.texte_fr);
    }
    return `<p class="muted" style="font-size:.85rem">${escapeHtml(t("report_not_generated"))}</p>`;
  }
  return reportRecitHtml(texte);
}

function reportBodyHtml(s){
  return reportMode === "raw" ? reportRawHtml(s) : reportNarrativeBodyHtml();
}

// Lot R2 §4/§5 : charge l'état du rapport rédigé (GET .../report, lecture
// ouverte à tous -- R79) pour la session ouverte. Distinct de
// CURRENT_SESSION (qui ne porte que les vols pour le Brut) : le Récit et
// son empreinte vivent dans une table à part (debrief_report).
async function fetchReportData(sessionId){
  try {
    REPORT_DATA = await apiFetch(`/api/debrief/sessions/${sessionId}/report`);
  } catch(e){
    // Échec de LECTURE (réseau, 404 session, etc.) -- distinct d'un échec
    // de RÉDACTION (reportGenError, cf. onReportGenerateClick). On retombe
    // sur l'état vide plutôt que de laisser `null` bloquer indéfiniment
    // sur "chargement...".
    REPORT_DATA = { exists:false, texte_fr:null, texte_en:null, a_corriger:false };
  }
  if(!$("#modal-report").classList.contains("hidden")) renderModalReport();
}

async function onReportGenerateClick(){
  if(estInviteEcran()){ showToast(t("invite_lecture_seule")); return; } // lot « L'accès invité » (R11)
  if(reportGenBusy || !CURRENT_SESSION) return;
  reportGenBusy = true;
  reportGenError = null;
  renderModalReport();
  // Lot R6 §5③ -- la route rend la main immédiatement (202) : c'est
  // désormais l'état serveur (`REPORT_DATA.redaction_en_cours`, §5②) qui
  // grise le bouton, plus l'attente de ce clic. `apiFetch` porte le code
  // HTTP sur l'erreur qu'elle lève (`err.status`, depuis le v1.0038) ; on
  // garde ici le `fetch` brut, même patron que `deleteDebriefSession` un
  // peu plus haut, pour isoler le 409 et le 429 sans passer par une levée.
  try {
    const res = await fetch(`/api/debrief/sessions/${CURRENT_SESSION.id}/report`, {
      method: "POST", credentials: "same-origin",
    });
    if(res.status === 409){
      // Le 409 s'affiche comme un état, pas comme une erreur : quelqu'un
      // a été plus rapide, ce n'est pas une panne. On ne pose pas
      // `reportGenError` (zone alarme, --sev-down) -- la lecture (GET,
      // ci-dessous) porte la vérité de qui rédige, et `renderModalReport`
      // affichera la bannière `#report-gen-busy` à partir de là.
      await fetchReportData(CURRENT_SESSION.id);
      // Lot « Le Débrief : quatre défauts » : le 409 vaut aussi pour « Statistiques
      // périmées ». Si la relecture ne montre aucune rédaction en cours, ce n'est
      // pas « quelqu'un rédige » : on le dit, au lieu de ne rien afficher.
      if(!(REPORT_DATA && REPORT_DATA.redaction_en_cours)){
        reportGenError = t("report_stale_blocked");
      }
    } else if(res.status === 429){
      // Lot « Polish du moteur du Débrief » : le refus de plafond se lit
      // dans la langue de l'écran ; la route garde son `detail`.
      reportGenError = t("report_cap_reached");
    } else if(!res.ok){
      let detail = "";
      try { const j = await res.json(); detail = j && j.detail; } catch(e){ /* pas de corps JSON */ }
      reportGenError = detail || t("report_gen_error_generic");
    } else {
      REPORT_DATA = await res.json();
    }
  } catch(e){
    // Repli R2 §4 : le fournisseur ne répond pas (ou plafond atteint) =>
    // AUCUN rapport n'est écrit côté serveur -- REPORT_DATA n'est PAS
    // touché ici, l'éventuel rapport précédent reste affiché tel quel.
    // L'interface le dit (brief §4), sans texte de secours.
    reportGenError = e.message || t("report_gen_error_generic");
  }
  reportGenBusy = false;
  renderModalReport();
}

function renderModalReport(){
  const s = CURRENT_SESSION;
  if(!s) return;
  $("#report-subject").textContent = `${(s.sim||"").toUpperCase()} · ${s.display_title||""}`;
  $("#report-narrative-btn").classList.toggle("is-active", reportMode==="narrative");
  $("#report-raw-btn").classList.toggle("is-active", reportMode==="raw");
  $("#report-body").innerHTML = reportBodyHtml(s);

  // Tampon R80 -- "à corriger" quand l'empreinte du rapport stocké diverge
  // de la fiche courante. Un rapport dépassé reste affiché (le tampon ne
  // le cache jamais) ; jamais affiché tant qu'aucun rapport n'existe.
  const stamp = $("#report-stamp");
  stamp.classList.toggle("hidden", !(REPORT_DATA && REPORT_DATA.exists && REPORT_DATA.a_corriger));

  // Bouton Rédiger/Réécrire -- réservé aux éditeurs de la session (R79) ;
  // masqué, pas seulement désactivé, pour qui ne peut pas éditer : la
  // lecture est ouverte à tous, la rédaction ne l'est pas.
  const btn = $("#report-generate-btn");
  const canEdit = !!s.can_edit;
  btn.classList.toggle("hidden", !canEdit);
  if(canEdit){
    // Lot R6 §5② -- ne croit plus SEULEMENT la variable locale : l'état
    // serveur (`redaction_en_cours`, porté par la lecture) grise le
    // bouton chez TOUS tant qu'une rédaction tourne sur cette session, pas
    // seulement chez qui l'a lancée. `reportGenBusy` ne survit que pour
    // l'intervalle entre le clic et la réponse du 202.
    // Lot « Le Débrief : quatre défauts » : une session à recalculer grise aussi
    // le bouton (la route répondrait 409 « Statistiques périmées »).
    btn.disabled = reportGenBusy || (REPORT_DATA && REPORT_DATA.redaction_en_cours) || !!s.stats_stale;
    btn.textContent = reportGenBusy
      ? t("report_generating")
      : t(REPORT_DATA && REPORT_DATA.exists ? "report_regenerate_btn" : "report_generate_btn");
  }

  // Lot R6 §5④ -- information d'état, pas une action : affichée pour TOUS
  // ceux qui ouvrent la modale, éditeurs ou non (la lecture est ouverte à
  // tous). Le nom ne va pas dans le bouton (il déborderait au palier
  // compact, brief §5④) -- ici seulement, dans sa propre zone.
  const busy = $("#report-gen-busy");
  const redactionEnCours = !!(REPORT_DATA && REPORT_DATA.redaction_en_cours);
  // Lot « Le Débrief : quatre défauts » : à défaut de rédaction en cours, un
  // éditeur voit pourquoi « Rédiger » est grisé sur une session à recalculer.
  const staleBloque = canEdit && !!s.stats_stale && !redactionEnCours;
  busy.classList.toggle("hidden", !(redactionEnCours || staleBloque));
  if(redactionEnCours){
    busy.textContent = REPORT_DATA.redaction_par
      ? t("report_busy_by").replace("{name}", REPORT_DATA.redaction_par)
      : t("report_busy_conflict");
  } else if(staleBloque){
    busy.textContent = t("report_stale_blocked");
  }

  const status = $("#report-gen-error");
  status.classList.toggle("hidden", !reportGenError);
  if(reportGenError) status.textContent = reportGenError;
}

function openModalReport(){
  if(!CURRENT_SESSION) return;
  reportMode = "narrative";
  REPORT_DATA = null;
  reportGenError = null;
  renderModalReport();
  $("#modal-report").classList.remove("hidden");
  rrFenetreOuverte({t:"rapport"});   // lot « Le retour et l'adresse » : une entrée de plus
  fetchReportData(CURRENT_SESSION.id);
}
function closeModalReport(){
  $("#modal-report").classList.add("hidden");
  rrFenetreFermee("report");   // lot « Le retour et l'adresse » : la fermeture consomme son entrée
}

function wireModalReport(){
  const overlay = $("#modal-report");
  if(!overlay) return;
  overlay.querySelectorAll("[data-close]").forEach(b=> b.addEventListener("click", closeModalReport));
  overlay.addEventListener("click", (e)=>{ if(e.target === overlay) closeModalReport(); });
  $("#report-narrative-btn").addEventListener("click", ()=>{ reportMode = "narrative"; renderModalReport(); });
  $("#report-raw-btn").addEventListener("click", ()=>{ reportMode = "raw"; renderModalReport(); });
  $("#report-generate-btn").addEventListener("click", onReportGenerateClick);
}

function wireMissionsMount(){
  const mount = $("#missions-mount");
  if(!mount) return;
  mount.addEventListener("click", (e)=>{
    const chip = e.target.closest("[data-chip]");
    if(chip){
      const group = chip.dataset.chipGroup;
      if(group === "squadron") missionsFilters.squadron = chip.dataset.chip;
      if(group === "year"){ missionsFilters.year = chip.dataset.chip; missionsFilters.month = "all"; }
      if(group === "month") missionsFilters.month = chip.dataset.chip;
      renderMissions();
      return;
    }
    const depBtn = e.target.closest("[data-open-deposer]");
    if(depBtn){ openModalDeposer(); return; }
    const retryBtn = e.target.closest("[data-missions-retry]");
    if(retryBtn){ loadMissions(); return; }
    // Chgt 4 : suppression admin -- vérifié AVANT data-open-session (le
    // bouton est imbriqué dans la carte), jamais sans confirmation.
    const delBtn = e.target.closest("[data-delete-session]");
    if(delBtn){ deleteDebriefSession(delBtn.dataset.deleteSession, delBtn); return; }
    // Lot « L'écran C » : la pastille de campagne ouvre C (écoute déléguée), jamais la session.
    if(e.target.closest("[data-ouvre-campagne]")) return;
    const card = e.target.closest("[data-open-session]");
    if(card){ openSession(card.dataset.openSession); return; }
  });
  mount.addEventListener("keydown", (e)=>{
    if(e.key!=="Enter" && e.key!==" ") return;
    if(e.target.closest("[data-delete-session]")) return; // le <button> gère lui-même Entrée/Espace
    if(e.target.closest("[data-ouvre-campagne]")) return; // Lot « L'écran C » : le lien s'ouvre nativement
    const card = e.target.closest("[data-open-session]");
    if(card){ e.preventDefault(); openSession(card.dataset.openSession); }
  });
  mount.addEventListener("change", (e)=>{
    if(e.target.id === "sim-select"){
      missionsFilters.sim = e.target.value;
      renderMissions();
    }
  });
}

/* ================= Lot D2③ : modale Déposer ================= */

function inferKind(filename){
  const lower = (filename||"").toLowerCase();
  if(lower.endsWith(".acmi")) return "acmi"; // couvre aussi ".zip.acmi"
  return "debrief"; // .log/.txt + repli par défaut (override possible)
}

function addFilesToQueue(fileList){
  Array.from(fileList||[]).forEach(file=>{
    deposerQueue.push({
      id: "f" + Math.random().toString(36).slice(2),
      file,
      kind: inferKind(file.name),
      status: "pending",
      error: null,
    });
  });
  if(deposerPhase === "done"){
    // Ajout de fichiers après un dépôt terminé : le bouton doit revenir en
    // mode "Déposer" (sinon un clic déclencherait resetDeposerQueue() et
    // effacerait la sélection qu'on vient de faire).
    deposerPhase = "select";
    $("#btn-do-upload").textContent = t("deposer_submit");
  }
  renderDeposerFileList();
}

function updateDepositorFieldVisibility(){
  const needsDepositor = deposerQueue.some(f=> f.kind==="debrief");
  $("#field-depositor").classList.toggle("hidden", !needsDepositor);
}

function renderDeposerFileList(){
  const list = $("#deposer-file-list");
  list.innerHTML = deposerQueue.map(entry=>{
    const cls = entry.status==="error" ? "err" : (entry.status==="ok" ? "ok" : "");
    const statusSuffix = entry.status==="uploading" ? ` — ${escapeHtml(t("deposer_in_progress"))}` : "";
    const disabled = (entry.status==="uploading" || entry.status==="ok") ? "disabled" : "";
    return `<div class="file-row ${cls}" data-file-id="${entry.id}">
      <span class="fn">${escapeHtml(entry.file.name)}${statusSuffix}</span>
      <span class="fs">${escapeHtml(fmtFileSize(entry.file.size))}</span>
      <select data-file-id="${entry.id}" ${disabled}>
        <option value="debrief" ${entry.kind==="debrief"?"selected":""}>${escapeHtml(t("kind_debrief"))}</option>
        <option value="acmi" ${entry.kind==="acmi"?"selected":""}>${escapeHtml(t("kind_acmi"))}</option>
      </select>
      <button type="button" class="file-remove" data-file-id="${entry.id}" ${entry.status==="uploading"?"disabled":""} aria-label="${escapeHtml(t("deposer_remove_file"))}">×</button>
      ${entry.status==="error" ? `<span class="file-err-msg">${escapeHtml(entry.error)}</span>` : ""}
    </div>`;
  }).join("");
  updateDepositorFieldVisibility();
}

function populateDepositorSelect(){
  const sel = $("#depositor-select");
  const all = Array.from(PROFILES.values());
  const meId = ME ? String(ME.id) : null;
  const others = all.filter(p=> String(p.id)!==meId).sort((a,b)=> (a.name||"").localeCompare(b.name||""));
  const me = meId ? all.find(p=> String(p.id)===meId) : null;
  const ordered = me ? [me, ...others] : others;
  sel.innerHTML = ordered.map(p=>{
    const isMe = meId && String(p.id)===meId;
    const label = isMe ? `${p.name} (${t("deposer_me")})` : p.name;
    return `<option value="${escapeHtml(String(p.id))}">${escapeHtml(label)}</option>`;
  }).join("");
  if(meId) sel.value = meId;
}

function resetDeposerQueue(){
  deposerQueue = [];
  deposerPhase = "select";
  $("#deposer-file-list").innerHTML = "";
  $("#deposer-results").innerHTML = "";
  $("#field-depositor").classList.add("hidden");
  $("#mission-name-input").value = "";
  $("#wing-note-input").value = "";
  $("#campaign-select").value = "";
  $("#nature-select").value = "mission";
  $("#deposer-status").classList.add("hidden");
  $("#btn-do-upload").disabled = false;
  $("#btn-do-upload").textContent = t("deposer_submit");
}

async function openModalDeposer(campaignId){
  resetDeposerQueue();
  populateDepositorSelect();
  $("#modal-deposer").classList.remove("hidden");
  rrFenetreOuverte({t:"deposer", camp: campaignId || null});   // lot « Le retour et l'adresse » : une entrée de plus
  // Lot 2.3 §4.8a : chargée paresseusement -- premier ouverture de la
  // modale déclenche le fetch, les suivantes réutilisent le cache.
  // Lot 3.4 §5 : aucun simulateur n'est encore connu à ce stade (il se
  // déduit du fichier après upload) -- "dcs" assumé, seul geste de ce lot
  // sur le module Débrief.
  await ensureCampaignsLoaded("dcs");
  // Lot « Déposer depuis la barre du haut » : depuis la fiche d'une campagne, elle est préchoisie si le dépôt peut s'y rattacher.
  $("#campaign-select").innerHTML = campaignOptionsHtml(campaignId || "");
}
/* Lot « Déposer depuis la barre du haut » : le bouton « Déposer » vit dans la barre du haut, sur tous les écrans du
   Débrief (au téléphone, le bouton rond) ; depuis la fiche d'une campagne, la modale s'ouvre sur cette campagne. Après
   un dépôt réussi, les écrans qui montrent les missions se relisent : l'écran affiché tout de suite, les autres à leur
   prochaine ouverture. */
$("#debrief-deposer-btn").addEventListener("click", ()=>{
  const ecran = debriefStack[debriefStack.length - 1];
  openModalDeposer(ecran === "campagne" ? CURRENT_CAMPAIGN_ID : null);
});

function debriefApresDepot(){
  escadreLoadState = "idle";
  accueilLoadState = "idle";
  dossierLoadState = "idle";
  campagnesLoadState = "idle";
  Object.keys(campagneLoadState).forEach(id=> delete campagneLoadState[id]);
  const ecran = debriefStack[debriefStack.length - 1];
  if(["accueil", "pilotes", "campagnes", "campagne", "escadrilles"].includes(ecran)) renderDebrief(ecran);
}

function closeModalDeposer(){
  if(deposerBusy) return; // dépôt en cours : pas de fermeture accidentelle
  $("#modal-deposer").classList.add("hidden");
  rrFenetreFermee("deposer");   // lot « Le retour et l'adresse » : la fermeture consomme son entrée
}

// Lot 2.1, addendum A2 : septième surface -- summary.display_title dans les
// deux branches (jamais summary.title, brut). sentName/sentNote = est-ce que
// CE dépôt a envoyé un nom/une note (connu du client, pas du résumé serveur)
// -- distingue "champ non envoyé" (aucune ligne) de "envoyé mais déjà défini".
function appendConfirmationCard(summary, sentName, sentNote){
  const noop = !!summary.no_op;
  const dateLabel = fmtSessionDateInline(summary.mission_date);
  const wrap = document.createElement("div");
  wrap.className = "upload-result" + (noop ? " noop" : "");
  if(noop){
    wrap.innerHTML = `<div class="h">${escapeHtml(t("deposer_noop"))}</div>
      <ul><li>${escapeHtml(t("deposer_attached_to"))} <b>${escapeHtml(summary.display_title||"")}</b> (${dateLabel})</li></ul>`;
  } else {
    const originLine = summary.session_created ? t("deposer_mission_created") : t("deposer_mission_joined");
    const nameLine = sentName ? (summary.name_applied ? t("deposer_name_applied") : t("deposer_name_already_set")) : null;
    const noteLine = sentNote ? (summary.note_applied ? t("deposer_note_applied") : t("deposer_note_already_set")) : null;
    wrap.innerHTML = `<div class="h">${escapeHtml(t("deposer_attached_to"))} « ${escapeHtml(summary.display_title||"")} » (${dateLabel})</div>
      <ul>
        <li>${escapeHtml(originLine)}</li>
        <li>${escapeHtml(t("deposer_n_uploads"))} : <b>${summary.n_uploads}</b></li>
        <li>${escapeHtml(t("deposer_n_flights"))} : <b>${summary.n_flights}</b></li>
        <li>${escapeHtml(t("deposer_n_kills"))} : <b>${summary.n_kills}</b></li>
        <li>${summary.acmi_present ? escapeHtml(t("acmi_on")) : escapeHtml(t("acmi_off"))}</li>
        ${nameLine ? `<li>${escapeHtml(nameLine)}</li>` : ""}
        ${noteLine ? `<li>${escapeHtml(noteLine)}</li>` : ""}
      </ul>`;
  }
  $("#deposer-results").appendChild(wrap);
}

async function handleDeposerSubmit(){
  if(deposerQueue.length === 0) return;
  const needsDepositor = deposerQueue.some(f=> f.kind==="debrief");
  const depositorVal = $("#depositor-select").value;
  if(needsDepositor && !depositorVal){ showToast(t("error_generic"), "erreur"); return; }

  // Lot 2.1 §4.4 : lus une seule fois, envoyés avec CHAQUE fichier de la
  // boucle -- c'est la règle serveur "si et seulement si le champ de la
  // session est vide" (idempotence, §6) qui garantit qu'un même nom ne
  // s'applique qu'une fois, jamais un filtrage côté client.
  const missionNameVal = $("#mission-name-input").value.trim();
  const wingNoteVal = $("#wing-note-input").value.trim();
  const campaignVal = $("#campaign-select").value;
  if(missionNameVal.length > 80 || wingNoteVal.length > 2000){
    showToast(t("error_field_too_long"), "erreur");
    return;
  }

  deposerBusy = true;
  $("#btn-do-upload").disabled = true;
  $("#deposer-status").classList.remove("hidden");
  $("#deposer-status").textContent = t("deposer_in_progress");

  let anyOk = false;
  let anyCampaignConflict = false;
  for(const entry of deposerQueue){
    if(entry.status === "ok") continue;
    entry.status = "uploading";
    renderDeposerFileList();
    try {
      const fd = new FormData();
      fd.append("file", entry.file);
      fd.append("kind", entry.kind);
      if(entry.kind === "debrief") fd.append("depositor", depositorVal);
      if(missionNameVal) fd.append("mission_name", missionNameVal);
      if(wingNoteVal) fd.append("wing_note", wingNoteVal);
      if(campaignVal) fd.append("campaign_id", campaignVal);
      fd.append("nature", $("#nature-select").value);
      const summary = await apiFetch("/api/debrief/upload", {method:"POST", body: fd});
      entry.status = "ok";
      anyOk = true;
      if(summary.campaign_conflict) anyCampaignConflict = true;
      renderDeposerFileList();
      appendConfirmationCard(summary, !!missionNameVal, !!wingNoteVal);
    } catch(e){
      entry.status = "error";
      entry.error = e.message || t("error_generic");
      renderDeposerFileList();
    }
  }

  $("#deposer-status").classList.add("hidden");
  deposerBusy = false;
  deposerPhase = "done";
  $("#btn-do-upload").disabled = false;
  $("#btn-do-upload").textContent = t("deposer_again");

  // Lot 2.3 §4.8a : le déposant doit savoir que son choix de campagne n'a
  // pas été appliqué, jamais le croire appliqué silencieusement.
  if(anyCampaignConflict) showToast(t("deposer_campaign_conflict"), "erreur");

  if(anyOk) await loadMissions(); // §C.3 : re-fetch + re-rendu Missions
  if(anyOk) debriefApresDepot();   // Lot « Déposer depuis la barre du haut »
}

function wireModalDeposer(){
  const overlay = $("#modal-deposer");
  const dz = $("#dz");
  const input = $("#dz-input");

  // Lot 2.3 §4.8a : champ injecté au runtime, pas dans index.html (P3 --
  // seuls styles.css et app.js sont amenés à changer ce lot). Même patron
  // .field que #field-mission-name/#field-depositor, posé une seule fois
  // ici (wireModalDeposer ne tourne qu'à l'init), jamais réinjecté à
  // chaque ouverture de modale.
  const missionNameField = $("#field-mission-name");
  if(missionNameField && !$("#field-campaign")){
    missionNameField.insertAdjacentHTML("afterend",
      `<div class="field" id="field-campaign">
        <label data-i18n="deposer_campaign_label">${escapeHtml(t("deposer_campaign_label"))}</label>
        <select id="campaign-select"></select>
      </div>`
    );
  }

  dz.addEventListener("click", ()=> input.click());
  dz.addEventListener("dragover", (e)=>{ e.preventDefault(); dz.classList.add("drag-over"); });
  dz.addEventListener("dragleave", ()=> dz.classList.remove("drag-over"));
  dz.addEventListener("drop", (e)=>{
    e.preventDefault();
    dz.classList.remove("drag-over");
    addFilesToQueue(e.dataTransfer.files);
  });
  input.addEventListener("change", ()=>{
    addFilesToQueue(input.files);
    input.value = "";
  });

  $("#deposer-file-list").addEventListener("click", (e)=>{
    const rmBtn = e.target.closest(".file-remove");
    if(rmBtn){
      deposerQueue = deposerQueue.filter(f=> f.id !== rmBtn.dataset.fileId);
      renderDeposerFileList();
    }
  });
  $("#deposer-file-list").addEventListener("change", (e)=>{
    if(e.target.matches("select[data-file-id]")){
      const entry = deposerQueue.find(f=> f.id===e.target.dataset.fileId);
      if(entry){ entry.kind = e.target.value; renderDeposerFileList(); }
    }
  });

  // Lot « Mission ou training » : choisir une campagne remet la nature sur Mission.
  overlay.addEventListener("change", (e)=>{
    if(e.target.id === "campaign-select" && e.target.value){
      $("#nature-select").value = "mission";
    }
  });

  $("#btn-do-upload").addEventListener("click", ()=>{
    if(deposerPhase === "done") resetDeposerQueue();
    else handleDeposerSubmit();
  });

  overlay.querySelectorAll("[data-close]").forEach(b=> b.addEventListener("click", closeModalDeposer));
  overlay.addEventListener("click", (e)=>{ if(e.target === overlay) closeModalDeposer(); });
}

/* ---------- Nav Débrief (Lot D2②) ----------
   Coquille + navigation uniquement -- aucun contenu (③④⑤ le peupleront).
   Pile de drill Missions→Session→Vol : les 5 racines du plan v4 sont des
   racines (reset de pile), "session"/"flight" s'empilent. Pattern repris
   de debrief_d2_mockup_v2.html (go/goTab/back), adapté aux #view-* du shell
   partagé plutôt qu'aux #screen-* standalone de la maquette.
   Lot 1.5b §14 — nav refaite en 5 entrées (source :
   SPEC_READY_ROOM_Debrief_Carriere_v1.md §4) : Accueil/Pilotes/Campagnes/
   Missions/Escadrilles remplacent les 2 anciennes entrées verrouillées. Racines
   citées en dur à 3 endroits (DEBRIEF_ROOTS, boucle ci-dessous, règle
   groupée styles.css) -- tenues cohérentes dans le même geste (§14). */
const DEBRIEF_ROOTS = ["accueil","pilotes","campagnes","missions","escadrilles"];
let debriefStack = ["accueil"]; // Lot « L'écran B » : l'accueil est l'écran d'arrivée.

function renderDebrief(screen){
  ["accueil","pilotes","campagnes","campagne","missions","escadrilles","escadrille","membre","session","flight"].forEach(s=>{
    const el = $("#view-"+s);
    if(el) el.classList.toggle("hidden", s!==screen);
  });
  const rootTab = DEBRIEF_ROOTS.includes(debriefStack[0]) ? debriefStack[0] : "missions";
  $$('[data-module-nav="debrief"] button[data-nav]').forEach(b=>{
    b.classList.toggle("active", b.dataset.nav===rootTab);
  });
  syncTopbarNavScroll();
  window.scrollTo(0,0);
  // Lot D2③ : peuplement réel de l'écran Missions (fetch au 1er affichage,
  // re-rendu depuis cache ensuite). Lot D2④ : peuplement réel de Session
  // (fetch/cache par id) ; Vol (⑤) reste un placeholder mécanique.
  if(screen === "missions") ensureMissionsLoaded();
  if(screen === "session") ensureSessionLoaded(CURRENT_SESSION_ID);
  if(screen === "flight") ensureFlightLoaded(CURRENT_FLIGHT_ID);
  if(screen === "escadrilles") ensureEscadreLoaded(); // Lot « L'écran D » (R177)
  // Lot « Les écrans E et F » : E se lit dans la charge de D ; F a sa route.
  if(screen === "escadrille") ensureEscadreLoaded();
  // Lot « L'écran B » : les chiffres et les escadrilles viennent de la charge de D.
  if(screen === "accueil"){ ensureEscadreLoaded(); ensureAccueilLoaded(); }
  if(screen === "membre") ensureMembreLoaded(CURRENT_MEMBER_ID);
  // Lot « L'écran A » : le dossier du pilote connecté ; l'escadre sert l'appareil de son escadrille (la photo).
  if(screen === "pilotes"){ ensureEscadreLoaded(); ensureDossierLoaded(); }
  // Lot « L'écran C — la fiche campagne » : le registre et la fiche ont leurs routes.
  if(screen === "campagnes") ensureCampagnesLoaded();
  if(screen === "campagne") ensureCampagneLoaded(CURRENT_CAMPAIGN_ID);
}

function goDebrief(screen, opts){
  opts = opts || {};
  if(opts.sessionId) CURRENT_SESSION_ID = opts.sessionId; // Lot D2③ §B.5
  if(opts.flightId) CURRENT_FLIGHT_ID = opts.flightId;    // Lot D2④
  if(opts.squadronId) CURRENT_SQUADRON_ID = opts.squadronId; // Lot « Les écrans E et F »
  if(opts.memberId) CURRENT_MEMBER_ID = opts.memberId;
  if(opts.campaignId) CURRENT_CAMPAIGN_ID = opts.campaignId; // Lot « L'écran C »
  if(opts.reset){
    debriefStack = [screen];
  } else if(DEBRIEF_ROOTS.includes(screen)){
    debriefStack = [screen];
  } else {
    const i = debriefStack.indexOf(screen);
    if(i>=0) debriefStack = debriefStack.slice(0, i+1);
    else debriefStack.push(screen);
  }
  // Lot « Le retour et l'adresse » (v1.0101) : l'historique suit la pile, une entrée par écran empilé.
  if(!RR.enDessin){
    const bas = (RR.etat && RR.etat.mod === "debrief") ? RR.etat.pile : [];
    rrPile("debrief", debriefStack.map((nom, i)=>
      (i < debriefStack.length - 1 && bas[i] && bas[i].e === nom) ? bas[i] : rrItem("debrief", nom)));
  }
  renderDebrief(screen);
}

/* ===================================================================
   Lot « L'écran D » (R177) — l'onglet « Escadrilles » du Débrief : l'escadre
   sur une seule page — état civil, ordre de bataille, activité, puis
   l'organigramme. Lecture seule, par une route propre au Débrief
   (GET /api/debrief/escadre). Les appareils d'une escadrille sont ceux
   qu'elle déclare au Centre (R176) ; leurs silhouettes, celles de l'écran
   vol (R172). Mobilier du catalogue (.idbar, .framed, .sec, .subsec, .list,
   .li, .stats) ; l'organigramme a ses règles propres (.og-*). Sans texte
   explicatif : le porteur les a retirés de la cible.
   =================================================================== */
let escadreLoadState = "idle"; // idle | loading | ready | error
let ESCADRE = null;

async function ensureEscadreLoaded(){
  if(escadreLoadState === "ready" || escadreLoadState === "loading"){ renderEscadre(); return; }
  escadreLoadState = "loading";
  renderEscadre();
  try {
    ESCADRE = await apiFetch("/api/debrief/escadre");
    escadreLoadState = "ready";
  } catch(e){
    escadreLoadState = "error";
  }
  renderEscadre();
}

/* ---------- Lot « L'écran B » -- l'accueil du Débrief, poste de commandement de
   l'escadre (R187) : les chiffres et les escadrilles de la charge de D, le reste de
   `GET /api/debrief/accueil` ; son décorum, de la famille de l'écran vol. ---------- */
let ACCUEIL = null;
let accueilLoadState = "idle";

async function ensureAccueilLoaded(){
  if(accueilLoadState === "ready" || accueilLoadState === "loading"){ renderAccueil(); return; }
  accueilLoadState = "loading";
  renderAccueil();
  try {
    ACCUEIL = await apiFetch("/api/debrief/accueil");
    accueilLoadState = "ready";
  } catch(e){
    accueilLoadState = "error";
  }
  renderAccueil();
}

function renderAccueil(){
  const mount = $("#accueil-mount");
  if(!mount) return;
  if(accueilLoadState === "ready" && escadreLoadState === "ready" && ACCUEIL && ESCADRE){
    mount.innerHTML = accueilHtml(ACCUEIL, ESCADRE);
    const souvenir = $("#accueil-souvenir");
    if(souvenir) souvenir.innerHTML = accueilDecorHtml();
    return;
  }
  const erreur = accueilLoadState === "error" || escadreLoadState === "error";
  mount.innerHTML = `<p class="muted">${escapeHtml(t(erreur ? "escadre_error" : "loading"))}</p>`;
}

// La photo du haut (le porteur, 1er octobre) : en haut à droite, elle chevauche le cadre
// des chiffres sans toucher son texte, et un trombone la tient sur le bord du papier --
// à 75 % de sa largeur, là où passe le bord de la feuille à tous les paliers.
function accueilPhotoHautHtml(){
  const jour = new Date().toISOString().slice(0, 10);
  return decorPhotoHautHtml(`${jour}|accueil`);
}

// Lot « L'écran C — la fiche campagne » : le tirage des deux photos de B, factorisé
// sur sa graine. B les tire sur le jour (`${jour}|accueil`) et ajoute son visa ; C les
// tire sur la campagne (`campagne|${id}`) : une campagne garde toujours les mêmes.
function decorPhotoHautHtml(graine){
  const h = decorumSeed(graine);
  const photoBas = h % 6;
  const photo = (photoBas + 1 + ((h >>> 17) % 5)) % 6;
  const rot = ((h >>> 22) % 7) - 3;
  const trombone = (h >>> 20) % 2;
  return `<span class="rr-pc acc-photo-haut" style="--rot:${rot}deg" aria-hidden="true">
    <img src="/static/assets/img/rr_photo_${photo + 1}.webp" alt="">
    <span class="acc-trombone"><img src="/static/assets/img/rr_trombone_${trombone + 1}.webp" alt=""></span>
  </span>`;
}

// Décorum de B (le porteur, 1er octobre) : de la famille de l'écran vol, sans la copier.
// Au pied de la feuille, en face du bloc NATO STANDARD : la photo du jour, tenue par
// deux scotchs en coin, et le visa daté du poste de commandement tamponné sur son
// coin. Tirage stable sur la date du jour : la photo change chaque jour, pas à
// chaque affichage. Rien dans le chemin de lecture.
function accueilDecorHtml(){
  const jour = new Date().toISOString().slice(0, 10);
  const h = decorumSeed(`${jour}|accueil`);
  const visaRot = -8 - ((h >>> 13) % 7);
  const lang = currentLang === "fr" ? "fr-FR" : "en-GB";
  const date = new Date().toLocaleDateString(lang, {day: "2-digit", month: "short", year: "numeric"}).toUpperCase().replace(".", "");
  return `${decorPhotoBasHtml(`${jour}|accueil`)}<span class="acc-visa" style="--rot:${visaRot}deg"><svg viewBox="0 0 120 120">
      <defs><path id="acc-visa-arc" d="M60,60 m-44,0 a44,44 0 1,1 88,0 a44,44 0 1,1 -88,0"/>
      <filter id="acc-visa-usure"><feTurbulence type="fractalNoise" baseFrequency=".9" numOctaves="2" seed="${h % 97}"/><feComponentTransfer><feFuncA type="discrete" tableValues="0 0 1 1 1"/></feComponentTransfer><feComposite in="SourceGraphic" operator="in"/></filter></defs>
      <g filter="url(#acc-visa-usure)" fill="none" stroke="currentColor">
        <circle cx="60" cy="60" r="56" stroke-width="3"/><circle cx="60" cy="60" r="50" stroke-width="1.2"/><circle cx="60" cy="60" r="31" stroke-width="1.2"/>
        <text font-size="10.5" letter-spacing="1.6" fill="currentColor" stroke="none"><textPath href="#acc-visa-arc" startOffset="2%">POSTE DE COMMANDEMENT · ${escapeHtml(wingDesignation().toUpperCase())} ·</textPath></text>
        <text x="60" y="56" text-anchor="middle" font-size="13" font-weight="700" letter-spacing="2" fill="currentColor" stroke="none">VISÉ</text>
        <text x="60" y="70" text-anchor="middle" font-size="7.5" letter-spacing=".8" fill="currentColor" stroke="none">${escapeHtml(date)}</text>
      </g></svg></span>`;
}

// Lot « L'écran C — la fiche campagne » : la photo aux scotchs de B, sans le visa,
// tirée sur sa graine (voir decorPhotoHautHtml).
function decorPhotoBasHtml(graine){
  const h = decorumSeed(graine);
  const photo = h % 6, s1 = (h >>> 4) % 4;
  const s2 = (s1 + 1 + ((h >>> 6) % 3)) % 4;
  const rot = ((h >>> 9) % 7) - 3;
  const scotch = n => `/static/assets/img/rr_scotch_${n + 1}.webp`;
  return `<span class="acc-photo" style="--rot:${rot}deg">
      <img src="/static/assets/img/rr_photo_${photo + 1}.webp" alt="">
      <span class="acc-scotch g"><img src="${scotch(s1)}" alt=""></span><span class="acc-scotch d"><img src="${scotch(s2)}" alt=""></span>
    </span>`;
}

function accueilHtml(a, d){
  const lang = currentLang === "fr" ? "fr-FR" : "en-GB";
  const actives = (d.squadrons || []).filter(s => s.status === "actif");
  const effectif = actives.reduce((n, s) => n + (s.members || []).length, 0) + (d.free_agents || []).length;
  const act = d.activity || {};
  const stat = (v, l) => `<div class="stat"><div class="v">${escapeHtml(String(v))}</div><div class="l">${escapeHtml(l)}</div></div>`;
  const chiffres = `<div class="framed acc-chiffres">
    <div class="sec ink">${escapeHtml(t("acc_chiffres_title"))}</div>
    <div class="stats">${stat(effectif, t("escadre_act_pilotes"))}${stat(act.hours != null ? act.hours + " h" : "—", t("escadre_act_heures"))}${stat(act.missions ?? "—", t("escadre_act_missions"))}${stat(act.campaigns ?? "—", t("escadre_act_campagnes"))}</div>
  </div>`;
  const chiffresDeco = chiffres.replace('<div class="framed acc-chiffres">', `<div class="framed acc-chiffres">${accueilPhotoHautHtml()}`);
  const msn = n => t("acc_msn").replace("{n}", n);
  // Correctifs (le porteur, 1er octobre) : une ou deux campagnes en cours au plus -- une ligne suffit.
  // Finitions (le porteur, 1er octobre) : le cadre ne montre que les campagnes en cours.
  // Lot « L'écran C » : une campagne en cours ouvre sa fiche.
  const camps = (a.campagnes || []).map(c => `<a class="acc-camp" href="#" data-ouvre-campagne="${escapeAttr(String(c.id))}"><span class="acc-camp-nom">${escapeHtml(c.name)}</span>${c.sim ? `<span class="camp ink">${escapeHtml(c.sim.toUpperCase())}</span>` : ""}<span class="a">${escapeHtml(msn(c.missions))}</span></a>`).join("");
  const campagnes = `<div class="framed">
    <div class="sec ink">${escapeHtml(t("acc_campagnes_title"))}</div>
    ${camps ? `<div class="acc-camps">${camps}</div>` : `<p class="muted">${escapeHtml(t("acc_aucune_campagne"))}</p>`}
  </div>`;
  // Lot « L'Accueil, durée et pilotes » : la barre et son calcul (maxVols) sont retirés ; la ligne porte la date et la durée, puis les pilotes.
  const pilotesN = n => t(n === 1 ? "escadre_pilotes_un" : "escadre_pilotes_n").replace("{n}", n);
  const missions = `<div class="framed">
    <div class="sec ink">${escapeHtml(t("acc_missions_title"))}</div>
    <div class="acc-missions">${(a.missions || []).map(x => `<a class="acc-mis" href="#" data-ouvre-session="${escapeAttr(String(x.session_id))}"><span class="acc-mis-l1"><span class="d">${escapeHtml((x.date ? new Date(x.date + "T12:00:00Z").toLocaleDateString(lang, {day: "2-digit", month: "short"}) : "—") + " · " + fmtDuree(x.duree_s))}</span><span class="a">${escapeHtml(pilotesN(x.pilotes || 0))}</span></span><span class="acc-mis-titre">${escapeHtml(x.titre || "—")}</span></a>`).join("")}</div>
  </div>`;
  const escadrilles = `<div class="framed">
    <div class="sec ink">${escapeHtml(t("acc_escadrilles_title"))}</div>
    <div class="list">${actives.map(sq => `<a class="li acc-esq" href="#" data-ouvre-escadrille="${sq.id}">${escadreCrestHtml(sq, "es-crest")}<span class="t2">${escapeHtml(sq.designation)}${sq.callsign ? ` <span class="acc-cs">« ${escapeHtml(sq.callsign)} »</span>` : ""}</span><span class="a">${escapeHtml([(sq.aircraft || []).join(" · "), pilotesN((sq.members || []).length)].filter(Boolean).join(" · "))}</span></a>`).join("")}</div>
  </div>`;
  const de = a.destructions || {};
  const destructions = sessionGraveyardPanelHtml(de, t("acc_destructions_title").replace("{n}", de.jours || 30));
  return chiffresDeco + campagnes + missions + escadrilles + destructions;
}

function renderEscadre(){
  renderAccueil();
  renderPilotes(); // Lot « L'écran A » : la photo du pilote lit l'appareil de son escadrille dans cette charge.
  renderEscadrille(); // Lot « Les écrans E et F » : E se lit dans la même charge.
  const mount = $("#escadrilles-mount");
  if(!mount) return;
  if(escadreLoadState === "ready" && ESCADRE){ mount.innerHTML = escadreHtml(ESCADRE); return; }
  const cle = escadreLoadState === "error" ? "escadre_error" : "loading";
  mount.innerHTML = `<p class="muted">${escapeHtml(t(cle))}</p>`;
}


/* ---------- Lot « Les écrans E et F » (R187, R188) ----------
   E, la fiche d'une escadrille ACTIVE, se lit dans la charge de D ; F, la
   synthèse d'un membre, a sa route. Trois chemins mènent à F : un membre de
   l'organigramme de D, un membre de celui de E, le nom d'un pilote identifié
   à l'écran d'un vol. Une escadrille en sommeil n'a pas de chemin vers E. */
let CURRENT_SQUADRON_ID = null;
let CURRENT_MEMBER_ID = null;
const MEMBRES = {};
const membreLoadState = {};

function renderEscadrille(){
  const mount = $("#escadrille-mount");
  if(!mount) return;
  const sq = ESCADRE && (ESCADRE.squadrons || []).find(s => String(s.id) === String(CURRENT_SQUADRON_ID));
  // Lot « Le retour et l'adresse » : l'escadrille se lit dans la charge de D ; ouverte par l'adresse, une escadrille absente
  // de la charge vaut une 404 (retour à Escadrilles).
  if(escadreLoadState === "ready" && !sq && rrChargeRefusee("escadrille", CURRENT_SQUADRON_ID, {status:404})) return;
  if(escadreLoadState === "ready" && sq){ rrChargeFaite("escadrille", CURRENT_SQUADRON_ID); mount.innerHTML = escadrilleHtml(sq, ESCADRE); return; }
  mount.innerHTML = `<p class="muted">${escapeHtml(t(escadreLoadState === "error" ? "escadre_error" : "loading"))}</p>`;
}

function fmtHeures(h){
  return (h == null ? 0 : h).toLocaleString(currentLang === "fr" ? "fr-FR" : "en-GB", {maximumFractionDigits: 1});
}

// Lot « Les heures de jour et de nuit » (v1.0068, R12) : la case des heures --
// « x h de jour / y h de nuit » -- partagée par le Dossier et la fiche membre
// (`membreStatsHtml`) et l'activité de l'escadrille (`escadrilleHtml`).
function heuresJourNuitStatHtml(jour, nuit, libelle){
  const g = (h, cle, sep) => `<span class="jn-g">${escapeHtml(fmtHeures(h))} h<span class="jn-k"> ${escapeHtml(t(cle))}</span>${sep}</span>`;
  return `<div class="stat jn1"><div class="v">${g(jour, "jn_de_jour", '<span class="jn-sep"> /</span>')} ${g(nuit, "jn_de_nuit", "")}</div><div class="l">${escapeHtml(libelle)}</div></div>`;
}

function escadrilleHtml(sq, d){
  const pilotesN = n => t(n === 1 ? "escadre_pilotes_un" : "escadre_pilotes_n").replace("{n}", n);
  const ms = sq.members || [];
  // Retouches (le porteur, 1er octobre) : la tête garde sa ligne à tous les paliers
  // (.esq-tete) ; les appareils de la dotation y figurent en fil de fer, à
  // droite -- les sept filaires du paquet, teintés par le thème.
  const sous = [sq.full_name, sq.callsign].filter(Boolean).join(" — ");
  const filaires = (sq.aircraft || []).map(nom => {
    const cle = escadreSilhouetteKey(nom);
    return cle ? `<figure class="esq-fil"><span class="filaire ac-${cle}"></span><figcaption>${escapeHtml(nom)}</figcaption></figure>` : "";
  }).join("");
  const idbar = `<div class="idbar"><div class="esq-tete">
    ${escadreCrestHtml(sq, "esq-crest")}
    <div class="esq-id"><div class="kick">${escapeHtml(t("esq_kick"))}</div><div class="esq-ttl"><span class="callsign ink worn">${escapeHtml(sq.designation)}</span><span class="esq-statut">${escapeHtml(t("esq_actif"))}</span></div>${sous ? `<div class="esq-nom">${escapeHtml(sous)}</div>` : ""}</div>
    ${filaires ? `<div class="esq-filaires">${filaires}</div>` : ""}
  </div></div>`;
  const kv = (l, v) => `<div class="li kv"><span class="d">${escapeHtml(l)}</span><span class="t2">${escapeHtml(v)}</span></div>`;
  const etat = `<div class="framed">
    <div class="sec ink">${escapeHtml(t("esq_etat_title"))}</div>
    <div class="es-duo">
      <div class="list">${kv(t("esq_identifiant"), sq.designation)}${kv(t("esq_nom_complet"), sq.full_name || "—")}${kv(t("esq_callsign"), sq.callsign || "—")}</div>
      <div class="list">${kv(t("esq_escadre"), (d.wing && d.wing.designation) || "—")}${kv(t("esq_dotation"), (sq.aircraft || []).join(" · ") || "—")}${kv(t("esq_effectif"), pilotesN(ms.length))}</div>
    </div>
  </div>`;
  // Lot « L'organigramme de E » : un arbre, à la manière de celui de l'escadre (écran D).
  // Le chef en haut ; sous lui, en retrait, l'adjoint d'abord puis les membres, dans l'ordre
  // de la charge. La liste se coupe en deux colonnes (les ⌈n/2⌉ premières à gauche) dès qu'elle
  // compte deux cases ; au palier compact la CSS la recolle en une seule colonne. Les cases
  // restent celles de escadrePiloteHtml (inchangée) : seule la mise en page est propre à E.
  const chef = ms.find(m => m.role === "leader");
  const liste = [
    ...ms.filter(m => m !== chef && m.role === "deputy"),
    ...ms.filter(m => m !== chef && m.role !== "deputy"),
  ];
  const deux = liste.length >= 2;
  const moitie = Math.ceil(liste.length / 2);
  const casesHtml = l => l.map(escadrePiloteHtml).join("");
  const colonnes = deux
    ? `<div class="esq-col">${casesHtml(liste.slice(0, moitie))}</div><div class="esq-col">${casesHtml(liste.slice(moitie))}</div>`
    : `<div class="esq-col">${casesHtml(liste)}</div>`;
  const organigramme = ms.length ? `<div class="framed">
    <div class="sec ink">${escapeHtml(t("esq_org_title"))}</div>
    <div class="esq-og${deux ? " deux" : ""}">
      ${chef ? `<div class="esq-chef">${escadrePiloteHtml(chef)}</div>` : ""}
      ${liste.length ? `<div class="esq-mem">${colonnes}</div>` : ""}
    </div>
  </div>` : "";
  const a = sq.activite || {};
  const stat = (v, l) => `<div class="stat"><div class="v">${escapeHtml(String(v))}</div><div class="l">${escapeHtml(l)}</div></div>`;
  const activite = `<div class="framed">
    <div class="sec ink">${escapeHtml(t("esq_act_title"))}</div>
    <div class="stats jn-large">${stat(a.missions ?? 0, t("esq_act_missions"))}${heuresJourNuitStatHtml(a.heures_jour, a.heures_nuit, t("esq_act_heures"))}${stat(a.sorties ?? 0, t("esq_act_sorties"))}${stat(a.pilotes ?? 0, t("esq_act_pilotes"))}</div>
  </div>`;
  // Le bilan de l'unité : le panneau même de la session, le calcul même côté serveur (R167).
  const bilan = sq.bilan ? sessionGraveyardPanelHtml(sq.bilan) : "";
  return idbar + etat + organigramme + activite + bilan;
}

async function ensureMembreLoaded(id){
  if(!id) return;
  if(membreLoadState[id] === "ready" || membreLoadState[id] === "loading"){ renderMembre(); return; }
  membreLoadState[id] = "loading";
  renderMembre();
  try {
    MEMBRES[id] = await apiFetch("/api/debrief/membres/" + encodeURIComponent(id));
    membreLoadState[id] = "ready";
    rrChargeFaite("membre", id);   // lot « Le retour et l'adresse »
  } catch(e){
    membreLoadState[id] = "error";
    if(rrChargeRefusee("membre", id, e)) return;   // ouverte par l'adresse : une 4xx ramène à Escadrilles
  }
  renderMembre();
}

function renderMembre(){
  const mount = $("#membre-mount");
  if(!mount) return;
  const id = CURRENT_MEMBER_ID;
  if(membreLoadState[id] === "ready" && MEMBRES[id]){ mount.innerHTML = membreHtml(MEMBRES[id]); return; }
  mount.innerHTML = `<p class="muted">${escapeHtml(t(membreLoadState[id] === "error" ? "mbr_error" : "loading"))}</p>`;
}

// Une barrette par campagne : sa teinte, tirée de la palette de la maquette
// DA, suit l'ordre de création des campagnes -- la même pour chaque pilote.
const RUBANS = [
  [[34, "var(--ink)", .85], [32, "var(--track)", 1], [34, "var(--ink)", .85]],
  [[28, "var(--ink-stamp)", .8], [44, "var(--track)", 1], [28, "var(--ink-stamp)", .8]],
  [[50, "var(--accent)", .75], [50, "var(--ink)", .8]],
  [[100, "var(--ink)", .55]],
  [[60, "var(--ink)", .85], [40, "var(--track)", 1]],
  [[45, "var(--ink-stamp)", .75], [55, "var(--ink)", .65]],
];
function rubanHtml(rang){
  const r = RUBANS[(Math.max(1, rang) - 1) % RUBANS.length];
  return `<span class="rib">${r.map(([w, c, o]) => `<i style="width:${w}%;background:${c};opacity:${o}"></i>`).join("")}</span>`;
}

// Lot « Polish de l'écran du Débrief » : la tête et la participation de F, servies aussi à A (le Dossier) --
// une seule définition. `apres` se pose à la fin de .mbr-tete (A y met son tampon personnel).
// Retouches (le porteur, 1er octobre) : l'écusson se pose sur le portrait, en patch ; la tête garde sa ligne à
// tous les paliers (.mbr-tete) ; la méta reste hors de la tête, à droite en grand écran, dessous ailleurs.
function membreTeteHtml(m, nom, apres = ""){
  const sq = m.squadron;
  const unite = sq ? sq.designation : (m.archived_at ? t("mbr_ancien") : t("escadre_free"));
  const statut = m.archived_at ? t("mbr_archive").replace("{d}", fmtLocalDate(m.archived_at)) : t("mbr_actif");
  return `<div class="idbar"><div class="mbr-tete">
    <span class="mbr-portrait"><span class="avatar mbr-av">${avatarHtml(m.id, m.avatar_hash, nom)}</span>${sq ? escadreCrestHtml(sq, "mbr-badge") : ""}</span>
    <div><div class="kick">${escapeHtml(t("mbr_kick").replace("{sq}", unite))}</div><div class="callsign ink worn">${escapeHtml(nom)}</div></div>${apres ? `
    ${apres}` : ""}
  </div><div class="meta"><b>${escapeHtml([unite, m.wing].filter(Boolean).join(" · "))}</b>${escapeHtml(statut)}</div></div>`;
}
// Les quatre chiffres de la participation (missions, temps, appareils, depuis).
function membreStatsHtml(p, lang){
  const depuis = p.depuis ? new Date(p.depuis + "T12:00:00Z").toLocaleDateString(lang, {month: "short", year: "numeric"}) : "—";
  const stat = (v, l) => `<div class="stat"><div class="v">${escapeHtml(String(v))}</div><div class="l">${escapeHtml(l)}</div></div>`;
  return `<div class="stats jn-large">${stat(p.missions ?? 0, t("mbr_missions"))}${heuresJourNuitStatHtml(p.heures_jour, p.heures_nuit, t("mbr_temps"))}${stat(p.appareils ?? 0, t("mbr_appareils"))}${stat(depuis, t("mbr_depuis"))}</div>`;
}

/* ---------- Lot « Les cartes DCS de chaque pilote » (v1.0085, R640) ----------
   Les cartes DCS qu'un pilote déclare posséder : la fiche F les montre en vignettes de la zone, le
   Dossier A les fait cocher et enregistrer, l'écran Escadrilles D en fait le tableau. La liste est
   `MAPS` (plus haut) ; toute liste de cartes à l'écran suit son ordre. */
const CARTES_CODES = {
  "Syria":"SYR", "Germany (Cold War)":"GCW", "Caucasus":"CAU", "Marianas":"MAR", "Normandy":"NOR",
  "Afghanistan":"AFG", "Persian Gulf":"PGF", "Sinai":"SIN", "Iraq":"IRQ", "Kola":"KOL",
  "South Atlantic":"SAT", "Nevada":"NEV", "The Channel":"CHN", "Marianas WWII":"M44"
};
const CARTES_GRATUITES = new Set(["Caucasus", "Marianas", "Marianas WWII"]);
let cdBrouillon = null;          // A : le Set des cartes cochées, null au chargement
let cdEdition = null;            // A : la sélection est-elle ouverte ? null au chargement
const cdLignesOuvertes = new Set(); // D : les clés des lignes d'escadrille dépliées
let cdEnvoi = false;             // A : un « Enregistrer » est en vol (addendum 1, A2)

// La vue de cartes : un tableau de noms (ou null = non déclaré), en vignettes, dans l'ordre de MAPS.
function cartesVueHtml(cartes){
  if(cartes == null) return `<p class="muted">${escapeHtml(t("cd_non_declarees"))}</p>`;
  const liste = MAPS.filter(c => cartes.includes(c));
  if(!liste.length) return `<p class="muted">${escapeHtml(t("cd_aucune"))}</p>`;
  const rot = [-1.6, 1.2, -0.8, 1.6, -1.2, 0.6];
  const vignettes = liste.map((c, i) => {
    const code = CARTES_CODES[c];
    return `<figure class="cd-insigne" style="--rot:${rot[i % 6]}deg"><img src="/static/assets/img/cartes/${code}.webp" alt="" loading="lazy"><figcaption><span class="cd-in-code">${escapeHtml(code)}</span><span class="cd-in-nom">${escapeHtml(c)}</span></figcaption>${CARTES_GRATUITES.has(c) ? `<span class="cd-in-free">${escapeHtml(t("cd_gratuite"))}</span>` : ""}</figure>`;
  }).join("");
  return `<div class="cd-insignes">${vignettes}</div>`;
}

function membreHtml(m){
  const lang = currentLang === "fr" ? "fr-FR" : "en-GB";
  const nom = callsign(m.name);
  const idbar = membreTeteHtml(m, nom);
  const participation = `<div class="framed">
    <div class="sec ink">${escapeHtml(t("mbr_part_title"))}</div>
    ${membreStatsHtml(m.participation || {}, lang)}
  </div>`;
  const servis = (m.appareils || []).map(a => `<div class="li">${aircraftSilhouetteHtml(a.type)}<span class="t2">${libTypeHtml(a.type)}</span><span class="a">${escapeHtml(t("mbr_msn").replace("{n}", a.missions).replace("{h}", fmtHeures(a.heures)))}</span></div>`).join("");
  // Lot « L'écran C » : une barrette ouvre la fiche de sa campagne.
  const rubans = (m.campagnes || []).map(c => `<a class="ribw" href="#" data-ouvre-campagne="${escapeAttr(String(c.id))}">${rubanHtml(c.rang)}<span class="rn">${escapeHtml(c.name)}</span></a>`).join("");
  const gauche = `<div class="framed">
    <div class="sec ink">${escapeHtml(t("mbr_servis_title"))}</div>
    ${servis ? `<div class="list">${servis}</div>` : `<p class="muted">${escapeHtml(t("mbr_aucune_mission"))}</p>`}
    <div class="sec ink mbr-sec2">${escapeHtml(t("mbr_barrettes_title"))}</div>
    ${rubans ? `<div class="ribs">${rubans}</div>` : `<p class="muted">${escapeHtml(t("mbr_aucune_barrette"))}</p>`}
  </div>`;
  const missions = (m.missions || []).map(x => `<a class="li mbr-mis" href="#" data-ouvre-session="${escapeAttr(String(x.session_id))}"><span class="d">${escapeHtml(x.date ? new Date(x.date + "T12:00:00Z").toLocaleDateString(lang, {day: "2-digit", month: "short"}) : "—")}</span><span class="mbr-mis-t"><span class="mbr-mis-titre">${escapeHtml(x.titre || "—")}</span>${x.campagne ? `<span class="camp ink">${escapeHtml(x.campagne)}</span>` : ""}</span></a>`).join("");
  const droite = `<div class="framed">
    <div class="sec ink">${escapeHtml(t("mbr_missions_title"))}</div>
    ${missions ? `<div class="list">${missions}</div>` : `<p class="muted">${escapeHtml(t("mbr_aucune_mission"))}</p>`}
  </div>`;
  // Lot « Les cartes DCS de chaque pilote » : le bloc des cartes, entre la participation et le duo.
  const cartes = `<div class="framed"><div class="sec ink">${escapeHtml(t("cd_cartes"))}</div>${cartesVueHtml(m.cartes_dcs)}</div>`;
  return idbar + participation + cartes + `<div class="duo">${gauche}${droite}</div>`;
}

/* ===================================================================
   Lot « L'écran A » (R208, R209, R211, R212, R213) — l'onglet « Pilotes » du
   Débrief : le dossier personnel du pilote connecté. LUI SEUL le voit, admins
   compris : la route (GET /api/debrief/dossier) ne prend aucun identifiant,
   l'écran n'a rien à filtrer. Neuf blocs dans l'ordre de R208, enfants directs
   de #pilotes-mount (contrat du banc v5, R211) : la tête et la participation de
   F ; le bilan de carrière et son panneau de destructions (celui de la session) ;
   la précision et les menaces (le vocabulaire de l'écran Vol) ; les appareils
   servis et les barrettes de F ; le carnet de vol ; le lien vers F. Les cadres
   viennent du mobilier du catalogue ; ce qui n'appartient qu'à A (le tampon, les
   bâtonnets, les lignes d'arme et de menace) vit sous #view-pilotes. Aucune
   donnée n'est lue ailleurs que dans le dossier et dans l'escadre (la photo).
   =================================================================== */
// Lot « Mission ou training » : la bascule « Tout · Missions · Training » du Dossier. Le choix se garde
// le temps de la session du navigateur (une variable de l'IIFE) ; il revient à « Tout » au rechargement.
let pilotesNature = "tout";
function pilotesNatureDs(d){
  const pn = (d.dossier || {}).par_nature;
  return (pilotesNature !== "tout" && pn && pn[pilotesNature]) || d.dossier || {};
}
function pilotesNatureFiltreHtml(d){
  if(!(d.dossier || {}).par_nature) return "";
  const b = (n, k) => `<button type="button" class="btn btn-sm${pilotesNature===n?" btn-accent":""}" data-pil-nature="${n}" aria-pressed="${pilotesNature===n}">${escapeHtml(t(k))}</button>`;
  return `<div class="pil-filtre"><span class="kick">${escapeHtml(t("pil_filtre_label"))}</span>${b("tout","pil_filtre_tout")}${b("mission","pil_filtre_missions")}${b("training","pil_filtre_training")}</div>`;
}
document.addEventListener("click", e=>{
  const b = e.target.closest && e.target.closest("[data-pil-nature]");
  if(b){ pilotesNature = b.dataset.pilNature; renderPilotes(); }
});

let DOSSIER = null;
let dossierLoadState = "idle"; // idle | loading | ready | error

// Lot « Les cartes DCS de chaque pilote » : les gestes du bloc « Mes cartes DCS » du Dossier. Une carte bascule
// dans le brouillon ; « Modifier » / « Replier » ouvre ou ferme la sélection et remet le brouillon aux cartes
// déclarées ; « Enregistrer » envoie le brouillon (dans l'ordre de MAPS) et recharge le Dossier de la réponse.
document.addEventListener("click", async e => {
  // Addendum 1 (A3) : un geste au clavier (`e.detail === 0`) rend le focus au contrôle de même clé après le rendu.
  const auClavier = e.detail === 0;
  const carte = e.target.closest && e.target.closest("[data-cd-carte]");
  if(carte){
    const c = carte.dataset.cdCarte;
    if(cdBrouillon.has(c)) cdBrouillon.delete(c); else cdBrouillon.add(c);
    renderPilotes();
    if(auClavier){ const b = Array.from(document.querySelectorAll("[data-cd-carte]")).find(x => x.dataset.cdCarte === c); if(b) b.focus(); }
    return;
  }
  if(e.target.closest && e.target.closest("[data-cd-modifier]")){
    cdEdition = !cdEdition;
    cdBrouillon = new Set((DOSSIER && DOSSIER.cartes_dcs) || []);
    renderPilotes();
    if(auClavier){ const b = document.querySelector("[data-cd-modifier]"); if(b) b.focus(); }
    return;
  }
  if(e.target.closest && e.target.closest("[data-cd-enregistrer]")){
    if(cdEnvoi) return; // Addendum 1 (A2) : un seul envoi à la fois
    cdEnvoi = true;
    try {
      DOSSIER = await apiFetch("/api/debrief/dossier/cartes", {
        method: "PUT",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({cartes: MAPS.filter(c => cdBrouillon.has(c))}),
      });
      cdEdition = false;
      cdBrouillon = new Set(DOSSIER.cartes_dcs || []);
      // Addendum 2 (A1) : D et F se relisent sans requête. Le membre d'ESCADRE, s'il est chargé, reçoit la
      // déclaration de la réponse (`escadreLoadState` n'est pas touché : le Dossier ne se vide pas) ; la fiche F
      // du membre se relit à sa prochaine ouverture.
      if(ESCADRE){
        const moi = String(DOSSIER.id);
        const membres = (ESCADRE.squadrons || []).flatMap(sq => sq.members || []).concat(ESCADRE.free_agents || []);
        membres.forEach(m => { if(String(m.id) === moi) m.cartes_dcs = DOSSIER.cartes_dcs; });
      }
      delete membreLoadState[String(DOSSIER.id)];
      renderPilotes();
    } catch(err){
      showToast(err.message || t("error_generic"), "erreur");
    } finally {
      cdEnvoi = false;
    }
  }
});

async function ensureDossierLoaded(){
  if(dossierLoadState === "ready" || dossierLoadState === "loading"){ renderPilotes(); return; }
  dossierLoadState = "loading";
  renderPilotes();
  try {
    DOSSIER = await apiFetch("/api/debrief/dossier");
    dossierLoadState = "ready";
  } catch(e){
    dossierLoadState = "error";
  }
  renderPilotes();
}

function renderPilotes(){
  const mount = $("#pilotes-mount");
  if(!mount) return;
  const attente = $("#pilotes-attente"); // « Chargement… » : hors du montage, dont les enfants sont les blocs.
  // La photo lit l'appareil de l'escadrille dans la charge de D : on attend qu'elle ait répondu (ou échoué :
  // sans escadre, la photo se tire alors parmi les douze).
  const escadreRepondue = escadreLoadState === "ready" || escadreLoadState === "error";
  if(dossierLoadState === "ready" && DOSSIER && escadreRepondue){
    mount.innerHTML = pilotesHtml(DOSSIER);
    if(attente) attente.hidden = true;
    return;
  }
  if(dossierLoadState === "error"){
    mount.innerHTML = `<p class="muted">${escapeHtml(t("mbr_error"))}</p>`;
    if(attente) attente.hidden = true;
    return;
  }
  mount.innerHTML = "";
  if(attente) attente.hidden = false;
}

// La photo du pilote (R213) : douze photos, deux familles. Le pilote tire dans la famille du premier appareil
// de son escadrille qui en a une ; sans escadrille, sans appareil déclaré ou avec un appareil hors des deux
// familles (JTAC, LotATC, saisie libre), il tire parmi les douze. Rien n'est stocké : la graine est
// l'identifiant du profil (en chaîne -- un identifiant Discord perd des chiffres en nombre) et le nom de la
// photo, la plus haute graine l'emporte, la première dans l'ordre à égalité.
const PILOTE_PHOTOS = ["h1","h2","h3","h4","h5","h6","j1","j2","j3","j4","j5","j6"];
const PILOTE_FAMILLES = {
  h: ["AH-64","CH-47","Mi-24P","Mi-8","OH-58D","SA-342 Gazelle","UH-1H"],
  j: ["A-10A","AJS-37","C-101","C-130","F-100","F-14A","F-14B","F-15C","F-16C","F/A-18","F-4E","F-5E","L-39","MB-339",
      "MIG-21Bis","MIG-29 FC3","MIG-29 FF","Mirage F1 CE","Mirage F1 EE","SU-25","SU-27"],
};

function pilotePhotoTirage(profilId, appareils){
  let famille = null;
  for(const code of appareils || []){
    famille = Object.keys(PILOTE_FAMILLES).find(k => PILOTE_FAMILLES[k].includes(code)) || null;
    if(famille) break;
  }
  let meilleur = null;
  PILOTE_PHOTOS.filter(nom => !famille || nom[0] === famille).forEach(nom => {
    const h = decorumSeed(`${String(profilId)}|${nom}`);
    if(meilleur === null || h > meilleur.h) meilleur = {nom, h};
  });
  return meilleur;
}

// La photo du pilote : la photo-souvenir de B (cadre crème, rotation tirée de la graine) scotchée -- deux bandes de
// scotch aux coins, comme la photo de l'accueil -- dans le cadre de l'ID Card, à côté de la participation. Pas de
// trombone : elle est collée (arbitrage du porteur, 8 octobre).
function pilotePhotoHtml(d){
  const sq = d.squadron && ESCADRE && (ESCADRE.squadrons || []).find(s => String(s.id) === String(d.squadron.id));
  const tirage = pilotePhotoTirage(d.id, sq ? sq.aircraft : []);
  const rot = ((tirage.h >>> 22) % 7) - 3;
  const s1 = (tirage.h >>> 20) % 4, s2 = (s1 + 1 + ((tirage.h >>> 6) % 3)) % 4;
  const scotch = n => `/static/assets/img/rr_scotch_${n + 1}.webp`;
  return `<span class="acc-photo pil-idphoto" style="--rot:${rot}deg" data-photo="${tirage.nom}" aria-hidden="true">
    <img src="/static/assets/img/rr_pilote_${tirage.nom}.webp" alt="">
    <span class="acc-scotch g"><img src="${scotch(s1)}" alt=""></span><span class="acc-scotch d"><img src="${scotch(s2)}" alt=""></span>
  </span>`;
}

// Le tampon PERSONNEL, dans la tête : un SVG écrit ici comme le visa de B (accueilDecorHtml), en encre de
// tampon, avec l'opacité et la rotation du visa (-8° à -14°). Un cadre double, le mot, et l'indicatif tapé à la
// machine dessous. Il reste dans le flux, jamais par-dessus un texte.
function pilotesTamponHtml(d, nom){
  const h = decorumSeed(`${String(d.id)}|personnel`);
  const rot = -8 - ((h >>> 13) % 7);
  const mot = t("pil_stamp");
  const indicatif = (nom || "").toUpperCase();
  const largeurMot = Math.round(mot.length * 14.4);
  const tapeAjuste = indicatif.length > 17 ? ` textLength="136" lengthAdjust="spacingAndGlyphs"` : "";
  return `<span class="pil-tampon" style="--rot:${rot}deg"><svg viewBox="0 0 168 74" role="img" aria-label="${escapeAttr(mot)}">
      <defs><filter id="pil-tampon-usure"><feTurbulence type="fractalNoise" baseFrequency=".9" numOctaves="2" seed="${h % 97}"/><feComponentTransfer><feFuncA type="discrete" tableValues="0 0 1 1 1"/></feComponentTransfer><feComposite in="SourceGraphic" operator="in"/></filter></defs>
      <g filter="url(#pil-tampon-usure)" fill="none" stroke="currentColor">
        <rect x="2" y="2" width="164" height="70" rx="3" stroke-width="3"/><rect x="8" y="8" width="152" height="58" rx="1.5" stroke-width="1.2"/>
        <text x="84" y="35" text-anchor="middle" font-size="21" font-weight="700" fill="currentColor" stroke="none" textLength="${largeurMot}" lengthAdjust="spacing" style="font-family:var(--font-label)">${escapeHtml(mot)}</text>
        <text x="84" y="56" text-anchor="middle" font-size="13" letter-spacing="1" fill="currentColor" stroke="none"${tapeAjuste} style="font-family:var(--font-typed)">${escapeHtml(indicatif)}</text>
      </g></svg></span>`;
}

// Les bâtonnets : une marque par destruction validée (air + sol), par paquets de cinq -- quatre traits et la
// barre --, trente au plus ; le total est toujours écrit à côté. Un graphique qui porte une information.
function pilotesBatonnetsHtml(total){
  const montrees = Math.min(total, 30);
  const traits = k => [3, 10, 17, 24].slice(0, k).map(x => `<line x1="${x}" y1="2" x2="${x}" y2="22"/>`).join("");
  const groupes = [];
  for(let i = 0; i < Math.floor(montrees / 5); i++) groupes.push(`<svg viewBox="0 0 30 24" aria-hidden="true">${traits(4)}<line x1="0" y1="19" x2="28" y2="5"/></svg>`);
  if(montrees % 5) groupes.push(`<svg viewBox="0 0 30 24" aria-hidden="true">${traits(montrees % 5)}</svg>`);
  const lib = t("pil_valid");
  return `<div class="pil-bat">
    ${groupes.length ? `<div class="pil-marks" role="img" aria-label="${escapeAttr(`${total} ${lib}`)}">${groupes.join("")}</div>` : ""}
    <div class="stat"><div class="v">${total}</div><div class="l">${escapeHtml(lib)}</div></div>
  </div>`;
}

// Le ratio : une décimale, la virgule en français ; un ratio nul s'écrit « 0 » ; sans perte (null), les mots.
function pilotesRatioHtml(ratio){
  const lang = currentLang === "fr" ? "fr-FR" : "en-GB";
  const sansPerte = ratio == null;
  const valeur = sansPerte ? t("pil_sans_perte") : (ratio === 0 ? "0" : ratio.toLocaleString(lang, {minimumFractionDigits: 1, maximumFractionDigits: 1}));
  return `<div class="pil-ratio"><div class="stat"><div class="v">${escapeHtml(valeur)}</div><div class="l">${escapeHtml(t(sansPerte ? "pil_sans_perte_cap" : "pil_ratio_cap"))}</div></div></div>`;
}

function pilotesNombreMot(n, cleUn, cleN){
  return t(n === 1 ? cleUn : cleN).replace("{n}", n);
}

// Lot « L'efficacité par arme au Dossier » : sous une arme dont des cibles ont été touchées, une ligne `.wx`
// « 13 détruites sur 21 touchées » ; sans cible touchée, rien (la ligne d'arme ne change pas).
function pilotesEfficaciteHtml(a){
  const n = a.cibles_touchees || 0;
  if(!(n > 0)) return "";
  const d = a.cibles_detruites || 0;
  const cle = d >= 2 ? "pil_eff_n_n" : (n >= 2 ? "pil_eff_1_n" : "pil_eff_1_1");
  return `<div class="wx">${escapeHtml(t(cle).replace("{d}", d).replace("{n}", n))}</div>`;
}

function pilotesPrecisionHtml(ds){
  // Lot « Correctif — le dossier du pilote » : plus de jauge (elle se lisait comme une précision moyenne) ;
  // une phrase dit combien de vols sont documentés, et que la précision ne porte que sur eux s'il y en a une part.
  const f = ds.vols_fiables || 0, n = ds.vols || 0;
  let phrase = t("pil_doc_cap").replace("{f}", f).replace("{n}", n);
  if(f > 0 && f < n) phrase += " " + t("pil_doc_partiel");
  const jauge = `<div class="note">${escapeHtml(phrase)}</div>`;
  // Lot « L'écran de la précision » : le canon et la famille des armes, servis par le dossier.
  const armes = ds.precision || [];
  const canon = ds.canon || [];
  const familles = ds.familles || {};
  const ligneArme = (a, affiche, titre) => {
    // Lot « L'écran de la précision » : une arme qui porte des salves se lit en salves au but sur salves.
    // Lot « Le Débrief : la précision des roquettes par salve » : même si elle a des tirs (la roquette), et une
    // roquette (famille 33) dit « roquettes tirées » ; les sous-munitions restent sur leurs largages.
    if(a.salves != null){
      const explication = familles[a.arme] === 33
        ? `${precNombre(a.tirs || 0, "prec_roq_1", "prec_roq_n")} ${precNombre(a.salves, "prec_salve_1", "prec_salve_n")}`
        : precSousSalves(a.largages || 0, a.salves);
      return precLigneRapportHtml(a.arme, affiche, a.salves_touchees || 0, a.salves, explication);
    }
    // Une arme larguée sans tir lié se dit en largages ; une arme qui a tiré, en tirs, touches et pourcentage.
    if(!a.tirs && a.largages){
      return `<div class="wpn"${titre}><span class="wn">${escapeHtml(affiche)}</span><span class="wv pil-larg">${escapeHtml(t("pil_largages").replace("{n}", a.largages))}</span></div>`;
    }
    const p = a.tirs ? Math.round(100 * a.touches / a.tirs) : 0;
    return `<div class="wpn"${titre}><span class="wn">${escapeHtml(affiche)}</span><span class="tk"><i style="width:${p}%"></i></span><span class="wv">${a.touches}/${a.tirs}</span><span class="wp">${p} %</span></div>`;
  };
  const types = armes.map(a => ({a, cle: precTypeCle(familles[a.arme])}));
  let lignes;
  if(!canon.length && precSansTypes(types)){
    // Sans famille ni canon : le cadre du v1.0028, noms entiers.
    lignes = armes.map(a => ligneArme(a, libArme(a.arme), precTitreArme(a.arme)) + pilotesEfficaciteHtml(a)).join("");
  } else {
    const affiches = precNomsAffiches(armes.map(a => a.arme).concat(canon.map(c => c.arme)));
    lignes = precGroupesHtml(
      types.map(({a, cle}) => ({cle, html: ligneArme(a, affiches.get(a.arme), ` title="${escapeAttr(a.arme)}"`) + pilotesEfficaciteHtml(a)}))
        .concat(canon.map(c => ({cle: "prec_cat_canon", html: precLigneRapportHtml(c.arme, affiches.get(c.arme),
          c.obus_au_but || 0, c.obus || 0, precSousCanon(c.obus || 0, c.rafales || 0, c.rafales_touchees || 0)) + pilotesEfficaciteHtml(c)})))
    );
  }
  const note = !ds.vols_fiables ? t("pil_prec_vide") : (!lignes ? t("pil_prec_aucun") : "");
  return `<div class="framed">
    <div class="sec ink">${escapeHtml(t("flight_precision_title"))}</div>
    ${jauge}${lignes}${note ? `<div class="note">${escapeHtml(note)}</div>` : ""}
  </div>`;
}

// Les menaces : une ligne par type d'initiateur ; la gravité se lit à la densité d'encre, comme sur l'écran Vol
// (engagement en encre pâle, touché en encre de sévérité, abattu en aplat).
function pilotesMenacesHtml(ds){
  const lignes = (ds.menaces || []).map(m => `<div class="li">
      <span class="t2">${m.type ? libTypeHtml(m.type) : escapeHtml(t("pil_inconnu"))}</span>
      <span class="sev am">${escapeHtml(pilotesNombreMot(m.engagements, "pil_engag_un", "pil_engag_n"))}</span>
      ${m.touche ? `<span class="sev ht">${escapeHtml(t("flight_grav_hit"))} ×${m.touche}</span>` : ""}
      ${m.abattu ? `<span class="sev dn">${escapeHtml(t("flight_grav_down"))} ×${m.abattu}</span>` : ""}
    </div>`).join("");
  return `<div class="framed">
    <div class="sec ink">${escapeHtml(t("pil_menaces_title"))}</div>
    ${lignes ? `<div class="list">${lignes}</div>` : `<p class="muted">${escapeHtml(t("pil_menaces_vide"))}</p>`}
  </div>`;
}

function pilotesCarnetHtml(ds){
  const lang = currentLang === "fr" ? "fr-FR" : "en-GB";
  const carnet = ds.carnet || [];
  const lignes = carnet.map((l, i) => {
    const issue = flightIssue(l.stats);
    const date = l.date ? new Date(l.date + "T12:00:00Z").toLocaleDateString(lang, {day: "2-digit", month: "short", year: "numeric"}) : "—";
    const detail = [l.appareil ? libType(l.appareil) : l.appareil, fmtDuree(l.duree_s), l.victoires ? pilotesNombreMot(l.victoires, "pil_vic_un", "pil_vic_n") : null].filter(Boolean).join(" · ");
    return `<div class="li pil-vol" role="link" tabindex="0" data-ouvre-vol="${escapeAttr(String(l.flight_id))}" data-vol-session="${escapeAttr(String(l.session_id))}"${i >= 10 ? " hidden" : ""}><span class="d">${escapeHtml(date)}</span><span class="mbr-mis-t"><span class="mbr-mis-titre">${escapeHtml(l.titre || "—")}</span>${l.campagne ? `<a class="camp ink" href="#" data-ouvre-campagne="${escapeAttr(String(l.campagne_id))}">${escapeHtml(l.campagne)}</a>` : ""}</span><span class="a">${escapeHtml(detail)}</span><span class="etat ${issue.key}">${escapeHtml(issue.label)}</span></div>`;
  }).join("");
  const tout = carnet.length > 10 ? `<button type="button" class="btn pil-tout" data-pil-tout>${escapeHtml(t("pil_tout").replace("{n}", carnet.length))}</button>` : "";
  return `<div class="framed">
    <div class="sec ink">${escapeHtml(t("pil_carnet_title"))}</div>
    <div class="list">${lignes}</div>
    ${tout}
  </div>`;
}

function pilotesHtml(d){
  const lang = currentLang === "fr" ? "fr-FR" : "en-GB";
  const ds = d.dossier || {};
  const nom = callsign(d.name);
  const stat = (v, l) => `<div class="stat"><div class="v">${escapeHtml(String(v))}</div><div class="l">${escapeHtml(l)}</div></div>`;

  // 1 · La tête de F, à l'identique ; s'y ajoute le tampon PERSONNEL.
  const tete = membreTeteHtml(d, nom, pilotesTamponHtml(d, nom));

  // 2 · La participation de F, et à côté son ID Card (arbitrage du porteur, 8 octobre) : un cadre qui porte la
  // photo du pilote, scotchée. Deux blocs côte à cote, dans un seul enfant du montage.
  const participation = `<div class="pil-ident"><div class="framed pil-part">
    <div class="sec ink">${escapeHtml(t("mbr_part_title"))}</div>
    ${membreStatsHtml(d.participation || {}, lang)}
  </div><div class="framed pil-id">
    ${pilotePhotoHtml(d)}
  </div></div>`;

  // Lot « Les cartes DCS de chaque pilote » : le bloc « Mes cartes DCS », juste avant le lien. Au premier rendu,
  // la sélection est ouverte tant que rien n'est déclaré, et le brouillon reprend les cartes déclarées.
  if(cdEdition === null){ cdEdition = d.cartes_dcs == null; cdBrouillon = new Set(d.cartes_dcs || []); }
  const declare = d.cartes_dcs != null;
  const etat = declare
    ? t("cd_declarees")
        .replace("{date}", d.cartes_dcs_le ? new Date(d.cartes_dcs_le).toLocaleDateString(lang, {day: "numeric", month: "long", year: "numeric"}) : "—")
        .replace("{n}", d.cartes_dcs.length).replace("{s}", d.cartes_dcs.length > 1 ? "s" : "")
    : t("cd_non_declarees");
  const choix = c => {
    const coche = cdBrouillon.has(c);
    return `<button type="button" class="btn btn-sm${coche ? " btn-accent" : ""}" data-cd-carte="${escapeAttr(c)}" aria-pressed="${coche}">${coche ? "✓ " : ""}${escapeHtml(c)}</button>`;
  };
  const pied = `<div class="cd-pied"><span class="cd-etat">${escapeHtml(etat)}</span>${cdEdition ? `<button type="button" class="btn btn-accent btn-sm" data-cd-enregistrer>${escapeHtml(t("cd_enregistrer"))}</button>` : ""}</div>`;
  const edition = `<div class="cd-edition">
      <div class="subsec">${escapeHtml(t("cd_payantes"))}</div><div class="cd-choix">${MAPS.filter(c => !CARTES_GRATUITES.has(c)).map(choix).join("")}</div>
      <div class="subsec">${escapeHtml(t("cd_gratuites"))}</div><div class="cd-choix">${MAPS.filter(c => CARTES_GRATUITES.has(c)).map(choix).join("")}</div>
      ${pied}
    </div>`;
  const cartes = `<div class="framed cd-dossier"><div class="cd-tete"><div class="sec ink">${escapeHtml(t("cd_mes_cartes"))}</div>${declare ? `<button type="button" class="btn btn-sm" data-cd-modifier aria-expanded="${cdEdition}">${escapeHtml(t(cdEdition ? "cd_replier" : "cd_modifier"))}</button>` : ""}</div>${declare ? cartesVueHtml(d.cartes_dcs) : ""}${cdEdition ? edition : pied}</div>`;

  // 9 · Le lien vers F : le dernier enfant du montage.
  const lien = `<div class="pil-lien"><a href="#" data-ouvre-membre="${escapeAttr(String(d.id))}">${escapeHtml(t("pil_voir_f"))}</a></div>`;

  // Le dossier vide : la tête, la participation à zéro, une mention, le lien.
  if(!ds.vols){
    return tete + participation + `<div class="framed"><p class="muted">${escapeHtml(t("pil_vide"))}</p></div>` + cartes + lien;
  }

  // 3a · Le bilan de carrière : les bâtonnets, le ratio, quatre chiffres.
  const dn = pilotesNatureDs(d);
  const v = dn.victoires || {}, pe = dn.pertes || {};
  const bilan = `<div class="framed">
    <div class="sec ink">${escapeHtml(t("pil_bilan_title"))}</div>
    ${pilotesBatonnetsHtml((v.air || 0) + (v.sol || 0))}
    ${pilotesRatioHtml(dn.ratio)}
    <div class="stats">${stat(v.air ?? 0, t("pil_air"))}${stat(v.sol ?? 0, t("pil_sol"))}${stat(pe.appareils ?? 0, t("pil_perdus"))}${stat(pe.ejections ?? 0, t("pil_ejections"))}</div>
  </div>`;
  // 3b · Les destructions par catégorie : le panneau de la session, tel quel.
  const destructions = sessionGraveyardPanelHtml(dn.bilan || {}, t("pil_destr_title"));

  // 6 · Les appareils de F, avec leurs victoires, leurs pertes et leur dernier vol (jointure par type) ;
  // 7 · les barrettes de F, dans le même cadre.
  const parAppareil = ds.par_appareil || {};
  const servis = (d.appareils || []).map(a => {
    const x = parAppareil[a.type] || {};
    const dernier = x.dernier ? new Date(x.dernier + "T12:00:00Z").toLocaleDateString(lang, {day: "2-digit", month: "short", year: "numeric"}) : "—";
    const bilanAppareil = [pilotesNombreMot(x.victoires || 0, "pil_vic_un", "pil_vic_n"), pilotesNombreMot(x.pertes || 0, "pil_perte_un", "pil_perte_n"), t("pil_dernier").replace("{d}", dernier)].join(" · ");
    return `<div class="li">${aircraftSilhouetteHtml(a.type)}<span class="t2">${libTypeHtml(a.type)}<span class="pil-app-s">${escapeHtml(bilanAppareil)}</span></span><span class="a">${escapeHtml(t("mbr_msn").replace("{n}", a.missions).replace("{h}", fmtHeures(a.heures)))}</span></div>`;
  }).join("");
  // Lot « L'écran C » : une barrette ouvre la fiche de sa campagne.
  const rubans = (d.campagnes || []).map(c => `<a class="ribw" href="#" data-ouvre-campagne="${escapeAttr(String(c.id))}">${rubanHtml(c.rang)}<span class="rn">${escapeHtml(c.name)}</span></a>`).join("");
  const appareils = `<div class="framed">
    <div class="sec ink">${escapeHtml(t("mbr_servis_title"))}</div>
    ${servis ? `<div class="list">${servis}</div>` : `<p class="muted">${escapeHtml(t("mbr_aucune_mission"))}</p>`}
    <div class="sec ink mbr-sec2">${escapeHtml(t("mbr_barrettes_title"))}</div>
    ${rubans ? `<div class="ribs">${rubans}</div>` : `<p class="muted">${escapeHtml(t("mbr_aucune_barrette"))}</p>`}
  </div>`;

  return tete + participation + pilotesNatureFiltreHtml(d)
    + `<div class="duo">${bilan}${destructions}</div>`
    + `<div class="duo">${pilotesPrecisionHtml(dn)}${pilotesMenacesHtml(ds)}</div>`
    + appareils + pilotesCarnetHtml(ds) + cartes + lien;
}

// Le carnet : une ligne ouvre son vol, au clic et à Entrée ; « Tout afficher » déplie la suite sur place.
// Le vol se lit dans SA session : openFlight ne porte que l'identifiant du vol (l'écran Vol lit CURRENT_SESSION_ID),
// la session se pose donc d'abord. L'attribut n'est pas data-ouvre-session : l'écoute déléguée plus bas ouvrirait la session.
function pilotesOuvreVol(ligne){
  CURRENT_SESSION_ID = ligne.dataset.volSession;
  openFlight(ligne.dataset.ouvreVol);
}
document.addEventListener("click", e => {
  // Lot « L'écran C » : la pastille de campagne d'une ligne ouvre C (écoute déléguée), jamais le vol.
  if(e.target.closest("[data-ouvre-campagne]")) return;
  const vol = e.target.closest("[data-ouvre-vol]");
  if(vol){ e.preventDefault(); pilotesOuvreVol(vol); return; }
  const tout = e.target.closest("[data-pil-tout]");
  if(tout){
    const suite = Array.from(document.querySelectorAll("#pilotes-mount .pil-vol[hidden]"));
    suite.forEach(l => { l.hidden = false; });
    tout.remove();
    if(suite[0]) suite[0].focus();
  }
});
document.addEventListener("keydown", e => {
  if(e.key !== "Enter") return;
  if(e.target.closest && e.target.closest("[data-ouvre-campagne]")) return; // Lot « L'écran C » : le lien s'ouvre nativement
  const vol = e.target.closest && e.target.closest("[data-ouvre-vol]");
  if(vol){ e.preventDefault(); pilotesOuvreVol(vol); }
});

/* ===================================================================
   Lot « L'écran C — la fiche campagne » (R209) — l'onglet « Campagnes » du
   Débrief : le registre des campagnes (#view-campagnes), puis la fiche d'une
   campagne (#view-campagne). Deux lectures du lot « Les campagnes — les
   données » : GET /api/debrief/campagnes et GET /api/debrief/campagnes/{id}.
   Le registre sur le patron de l'ordre de bataille de D ; la fiche sur le
   mobilier de D, E et F (tête, état civil, listes, paire, panneau du bilan) et
   le décorum de B, tiré sur la campagne. Aucune phrase explicative, aucune
   jauge, aucun chiffre de performance par participant (R208).
   =================================================================== */
let CURRENT_CAMPAIGN_ID = null;
let CAMPAGNES = null;
let campagnesLoadState = "idle"; // idle | loading | ready | error
const CAMPAGNE = {};
const campagneLoadState = {};    // par id : loading | ready | error | introuvable

async function ensureCampagnesLoaded(){
  if(campagnesLoadState === "ready" || campagnesLoadState === "loading"){ renderCampagnes(); return; }
  campagnesLoadState = "loading";
  renderCampagnes();
  try {
    CAMPAGNES = await apiFetch("/api/debrief/campagnes");
    campagnesLoadState = "ready";
  } catch(e){
    campagnesLoadState = "error";
  }
  renderCampagnes();
}

async function ensureCampagneLoaded(id){
  if(!id) return;
  if(campagneLoadState[id] === "ready" || campagneLoadState[id] === "loading"){ renderCampagne(); return; }
  campagneLoadState[id] = "loading";
  renderCampagne();
  try {
    CAMPAGNE[id] = await apiFetch("/api/debrief/campagnes/" + encodeURIComponent(id));
    campagneLoadState[id] = "ready";
    rrChargeFaite("campagne", id);   // lot « Le retour et l'adresse »
  } catch(e){
    // apiFetch porte le statut sur l'erreur : un 404 se reconnaît à lui, jamais au texte de la route.
    campagneLoadState[id] = e.status === 404 ? "introuvable" : "error";
    if(rrChargeRefusee("campagne", id, e)) return;   // ouverte par l'adresse : une 4xx ramène à Campagnes
  }
  renderCampagne();
}

function renderCampagnes(){
  const mount = $("#campagnes-mount");
  if(!mount) return;
  if(campagnesLoadState === "ready" && CAMPAGNES){ mount.innerHTML = campagnesHtml(CAMPAGNES); return; }
  mount.innerHTML = `<p class="muted">${escapeHtml(t(campagnesLoadState === "error" ? "cmp_erreur" : "loading"))}</p>`;
}

function renderCampagne(){
  const mount = $("#campagne-mount");
  if(!mount) return;
  const id = CURRENT_CAMPAIGN_ID;
  const mref = $("#campagne-mref");
  const souvenir = $("#campagne-souvenir");
  const c = CAMPAGNE[id];
  if(campagneLoadState[id] === "ready" && c){
    if(mref) mref.textContent = mrefText("CMP/" + String(c.rang).padStart(4, "0"));
    mount.innerHTML = campagneHtml(c);
    if(souvenir) souvenir.innerHTML = decorPhotoBasHtml(`campagne|${c.id}`);
    return;
  }
  if(mref) mref.textContent = mrefText("CMP/NNNN");
  if(souvenir) souvenir.innerHTML = "";
  const etat = campagneLoadState[id];
  const cle = etat === "introuvable" ? "cmp_introuvable" : (etat === "error" ? "cmp_erreur" : "loading");
  mount.innerHTML = `<p class="muted">${escapeHtml(t(cle))}</p>`;
}

// Une date de C s'écrit comme le visa de B : jour sur deux chiffres, mois court,
// année, en majuscules, sans point (« 17 AOÛT 2026 »).
function campagneDate(iso){
  const lang = currentLang === "fr" ? "fr-FR" : "en-GB";
  return new Date(iso + "T12:00:00Z").toLocaleDateString(lang, {day: "2-digit", month: "short", year: "numeric"}).toUpperCase().replace(".", "");
}

// La période, partout dans C : début → fin (close), début → en cours (en cours),
// « — » sans mission datée.
function campagnePeriode(c){
  const p = c.periode || {};
  if(!p.debut) return "—";
  const debut = campagneDate(p.debut);
  return c.status === "en_cours" ? t("cmp_periode_en_cours").replace("{d}", debut) : `${debut} → ${campagneDate(p.fin)}`;
}

function campagnesHtml(r){
  const toutes = r.campagnes || [];
  if(!toutes.length) return `<p class="muted">${escapeHtml(t("cmp_aucune"))}</p>`;
  const msn = n => t("acc_msn").replace("{n}", n);
  // L'ordre est celui de la route : on ne retrie rien.
  const ligne = c => `<a class="li cmp-li" href="#" data-ouvre-campagne="${escapeAttr(String(c.id))}">${rubanHtml(c.rang)}<span class="t2">${escapeHtml(c.name)}</span><span class="a">${escapeHtml(campagnePeriode(c) + " · " + msn(c.missions))}</span></a>`;
  const groupe = (cle, liste) => liste.length ? `<div class="subsec">${escapeHtml(t(cle))}</div><div class="list">${liste.map(ligne).join("")}</div>` : "";
  return `<div class="framed">
    <div class="sec ink">${escapeHtml(t("cmp_registre_title"))}</div>
    ${groupe("cmp_en_cours", toutes.filter(c => c.status === "en_cours"))}${groupe("cmp_closes", toutes.filter(c => c.status !== "en_cours"))}
  </div>`;
}

function campagneHtml(c){
  const lang = currentLang === "fr" ? "fr-FR" : "en-GB";
  const periode = campagnePeriode(c);
  const enCours = c.status === "en_cours";

  // La tête : la barrette, puis le titre ; à droite la période et le théâtre.
  const tete = `<div class="idbar"><div class="cmp-tete">${rubanHtml(c.rang)}
    <div><div class="kick">${escapeHtml(t("cmp_kick"))}</div><div class="callsign ink worn">${escapeHtml(c.name)}<span class="etat">${escapeHtml(t(enCours ? "cmp_en_cours" : "cmp_close"))}</span></div></div>
  </div><div class="meta"><b>${escapeHtml(periode)}</b>${escapeHtml(c.map_name || "")}</div></div>`;

  // Cadre 1 · l'ordre d'opérations : l'état civil de D et de E, puis la description
  // saisie au Centre (échappée, retours à la ligne gardés) ; sans elle, rien.
  // La photo au trombone de B s'y pose, tirée sur la campagne.
  const kv = (l, v) => `<div class="li kv"><span class="d">${escapeHtml(l)}</span><span class="t2">${escapeHtml(v)}</span></div>`;
  const act = c.activite || {};
  const description = (c.description || "").trim() ? `<div class="cmp-desc">${escapeHtml(c.description)}</div>` : "";
  const ordre = `<div class="framed">${decorPhotoHautHtml(`campagne|${c.id}`)}
    <div class="sec ink">${escapeHtml(t("cmp_ordre_title"))}</div>
    <div class="es-duo">
      <div class="list">${kv(t("cmp_theatre"), c.map_name || "—")}${kv(t("cmp_periode"), periode)}${kv(t("cmp_sim"), (c.sim || "—").toUpperCase())}</div>
      <div class="list">${kv(t("escadre_act_missions"), String(act.missions ?? 0))}${kv(t("cmp_sorties"), String(act.sorties ?? 0))}${kv(t("escadre_act_heures"), fmtHeures(act.heures) + " h")}${kv(t("cmp_pilotes"), String(act.pilotes ?? 0))}</div>
    </div>
    ${description}
  </div>`;

  // Cadre 2 · les missions : une ligne ouvre sa Session ; au-delà de dix, « Tout afficher » déplie la suite sur place.
  const ms = c.missions || [];
  const lignesMis = ms.map((x, i) => `<a class="li cmp-mis" href="#" data-ouvre-session="${escapeAttr(String(x.session_id))}"${i >= 10 ? " hidden" : ""}><span class="d">${escapeHtml(x.date ? new Date(x.date + "T12:00:00Z").toLocaleDateString(lang, {day: "2-digit", month: "short"}) : "—")}</span><span class="t2">${escapeHtml(x.titre || "—")}</span><span class="a">${escapeHtml(t("acc_vols").replace("{n}", x.vols || 0))}</span></a>`).join("");
  const tout = ms.length > 10 ? `<button type="button" class="btn cmp-tout" data-cmp-tout>${escapeHtml(t("pil_tout").replace("{n}", ms.length))}</button>` : "";
  const missions = `<div class="framed">
    <div class="sec ink">${escapeHtml(t("cmp_missions_title"))}</div>
    ${ms.length ? `<div class="list">${lignesMis}</div>${tout}` : `<p class="muted">${escapeHtml(t("cmp_aucune_mission"))}</p>`}
  </div>`;

  // La paire · les participants, en ordre alphabétique du nom affiché (aucun autre chiffre que les missions), et le bilan sans nom.
  const parts = (c.participants || []).map(p => ({...p, nom: callsign(p.name)}))
    .sort((a, b) => String(a.nom || "").localeCompare(String(b.nom || ""), currentLang, {sensitivity: "base"}));
  const lignesPart = parts.map(p => `<a class="li cmp-part" href="#" data-ouvre-membre="${escapeAttr(String(p.id))}"><span class="t2">${escapeHtml(p.nom || "—")}</span>${p.escadrille ? `<span class="camp ink">${escapeHtml(p.escadrille)}</span>` : ""}<span class="a">${escapeHtml(t("acc_msn").replace("{n}", p.missions))}</span></a>`).join("");
  const participants = `<div class="framed">
    <div class="sec ink">${escapeHtml(t("cmp_participants_title"))}</div>
    ${lignesPart ? `<div class="list">${lignesPart}</div>` : `<p class="muted">${escapeHtml(t("cmp_aucun_participant"))}</p>`}
  </div>`;
  const bilan = sessionGraveyardPanelHtml(c.bilan || {}, t("cmp_bilan_title"));

  return tete + ordre + missions + `<div class="duo">${participants}${bilan}</div>`;
}

// « Tout afficher » : la suite des missions se déplie sur place, le geste du carnet de A.
document.addEventListener("click", e => {
  const tout = e.target.closest("[data-cmp-tout]");
  if(!tout) return;
  const suite = Array.from(document.querySelectorAll("#campagne-mount .cmp-mis[hidden]"));
  suite.forEach(l => { l.hidden = false; });
  tout.remove();
  if(suite[0]) suite[0].focus();
});

// Les chemins vers E, vers F et vers une mission : écoute déléguée, posée une
// fois au chargement. Entrée ouvre aussi un membre au clavier.
// Lot « L'écran C » : et vers C, testé en premier -- la pastille d'une carte de
// Missions ou d'une ligne du carnet ouvre C, et seulement C.
document.addEventListener("click", e => {
  const cmp = e.target.closest("[data-ouvre-campagne]");
  if(cmp){ e.preventDefault(); goDebrief("campagne", {campaignId: cmp.dataset.ouvreCampagne}); return; }
  const esq = e.target.closest("[data-ouvre-escadrille]");
  if(esq){ e.preventDefault(); goDebrief("escadrille", {squadronId: esq.dataset.ouvreEscadrille}); return; }
  const mbr = e.target.closest("[data-ouvre-membre]");
  if(mbr){ e.preventDefault(); goDebrief("membre", {memberId: mbr.dataset.ouvreMembre}); return; }
  const ses = e.target.closest("[data-ouvre-session]");
  if(ses){ e.preventDefault(); goDebrief("session", {sessionId: ses.dataset.ouvreSession}); }
});
document.addEventListener("keydown", e => {
  if(e.key !== "Enter") return;
  const mbr = e.target.closest && e.target.closest("[data-ouvre-membre]");
  if(mbr){ e.preventDefault(); goDebrief("membre", {memberId: mbr.dataset.ouvreMembre}); return; }
  // Lot « Les heures de jour et de nuit » (R16) : la case d'une escadrille de
  // l'organigramme s'ouvre aussi à la touche Entrée (les liens <a> le font déjà d'eux-mêmes).
  const og = e.target.closest && e.target.closest(".og-sq[data-ouvre-escadrille]");
  if(og){ e.preventDefault(); goDebrief("escadrille", {squadronId: og.dataset.ouvreEscadrille}); }
});

// Le nom déclaré au Centre (« Mirage F1 EE ») rejoint les préfixes DCS de
// l'écran vol (« Mirage-F1… ») une fois ses espaces changés en tirets ;
// hors de la liste, aucune silhouette (R172). Une silhouette par famille.
function escadreSilhouetteKey(nom){
  const n = String(nom || "").trim().replace(/\s+/g, "-");
  const hit = AIRCRAFT_SILHOUETTE.find(([re]) => re.test(n));
  return hit ? hit[1] : null;
}

function escadreSilhouettesHtml(sq){
  const cles = [...new Set((sq.aircraft || []).map(escadreSilhouetteKey).filter(Boolean))];
  return cles.map(k => `<span class="wire ac-${k} es-sil" aria-hidden="true"></span>`).join("");
}

function escadreCrestHtml(sq, cls){
  if(sq.crest_sha){
    return `<img class="${cls}" src="/api/squadrons/${sq.id}/crest?v=${encodeURIComponent(sq.crest_sha)}" alt="">`;
  }
  return `<span class="${cls} vide" aria-hidden="true"></span>`;
}

function escadrePiloteHtml(m){
  const role = m.role === "leader" ? t("escadre_role_leader") : (m.role === "deputy" ? t("escadre_role_deputy") : "");
  const nom = callsign(m.name);
  // Lot « Les écrans E et F » : chaque membre d'un organigramme ouvre sa fiche F.
  return `<div class="og-pil${role ? " og-lead" : ""}" data-ouvre-membre="${escapeAttr(String(m.id))}" role="link" tabindex="0"><span class="avatar og-av">${avatarHtml(m.id, m.avatar_hash, nom)}</span><span class="og-cs">${escapeHtml(nom)}</span>${role ? `<span class="og-role">${escapeHtml(role)}</span>` : ""}</div>`;
}

function escadreHtml(d){
  const escadrilles = d.squadrons || [];
  const actives = escadrilles.filter(s => s.status === "actif");
  const dorment = escadrilles.filter(s => s.status !== "actif");
  const libres = d.free_agents || [];
  // Un seul effectif, arbitré par le porteur le 29 septembre : les pilotes de l'organigramme -- membres
  // des escadrilles actives et Free Agents. Il sert l'en-tête, l'état civil et la tête de
  // l'organigramme -- et les « pilotes actifs » de l'accueil, qui reprend le bloc « Activité »
  // de D (lot « L'écran B », R187) : les chiffres sont égaux par construction.
  const effectif = actives.reduce((n, s) => n + (s.members || []).length, 0) + libres.length;
  const pilotesN = n => t(n === 1 ? "escadre_pilotes_un" : "escadre_pilotes_n").replace("{n}", n);
  const designation = (d.wing && d.wing.designation) || "—";
  const sims = (d.sims || []).map(s => s.toUpperCase()).join(" · ") || "—";
  const activesN = t("escadre_actives_n").replace("{n}", actives.length);

  // Correctif « Le logo de l'escadre » : l'emblème ouvre la barre, à gauche du
  // titre, et grandit (demande du porteur, 30 septembre).
  const idbar = `<div class="idbar">
    <img class="es-logo" src="${wingEmblemSrc()}" alt="" data-wing-emblem>
    <div><div class="kick">${escapeHtml(t("escadre_kick"))}</div><div class="callsign ink worn">${escapeHtml(designation)}</div></div>
    <div class="meta"><b>${escapeHtml(activesN)}</b>${escapeHtml(pilotesN(effectif))}</div>
  </div>`;

  const kv = (l, v) => `<div class="li kv"><span class="d">${escapeHtml(l)}</span><span class="t2">${escapeHtml(v)}</span></div>`;
  const etat = `<div class="framed">
    <div class="sec ink">${escapeHtml(t("escadre_etat_title"))}</div>
    <div class="es-duo">
      <div class="list">${kv(t("escadre_designation"), designation)}${kv(t("escadre_nom_complet"), (WING && WING.full_name) || "—")}${kv(t("escadre_periode"), (WING && WING.period) || "—")}${kv(t("escadre_sim"), sims)}</div>
      <div class="list">${kv(t("escadre_actives"), String(actives.length))}${kv(t("escadre_sommeil"), String(dorment.length))}${kv(t("escadre_effectif"), pilotesN(effectif))}</div>
    </div>
  </div>`;

  const ligne = sq => {
    const corps = `${escadreCrestHtml(sq, "es-crest")}<span class="es-tag">${escapeHtml(sq.designation)}</span>${escadreSilhouettesHtml(sq)}<span class="es-ac">${escapeHtml((sq.aircraft || []).join(" · "))}</span><span class="es-n">${sq.status === "actif" ? escapeHtml(pilotesN((sq.members || []).length)) : "—"}</span>`;
    return sq.status === "actif"
      ? `<a class="li es-ob" href="#" data-ouvre-escadrille="${sq.id}">${corps}</a>`
      : `<div class="li es-ob dort">${corps}</div>`;
  };
  const orbat = `<div class="framed">
    <div class="sec ink">${escapeHtml(t("escadre_orbat_title"))}</div>
    <div class="subsec">${escapeHtml(t("escadre_orbat_actives"))}</div>
    <div class="list">${actives.map(ligne).join("")}</div>
    ${dorment.length ? `<div class="subsec">${escapeHtml(t("escadre_orbat_sommeil"))}</div><div class="list">${dorment.map(ligne).join("")}</div>` : ""}
  </div>`;

  const branche = sq => {
    const ms = sq.members || [];
    const tete = ms.filter(m => m.role === "leader" || m.role === "deputy");
    const reste = ms.filter(m => m.role !== "leader" && m.role !== "deputy");
    return `<div class="og-col" id="og-${sq.id}">
      <div class="og-sq" data-ouvre-escadrille="${sq.id}" role="link" tabindex="0">${escadreCrestHtml(sq, "og-crest")}<div class="og-sqt"><div class="og-id"><b>${escapeHtml(sq.designation)}</b><span class="og-sils">${escadreSilhouettesHtml(sq)}</span></div><span class="og-ac">${escapeHtml((sq.aircraft || []).join(" · "))}</span></div></div>
      ${tete.length ? `<div class="og-head">${tete.map(escadrePiloteHtml).join("")}</div>` : ""}
      ${reste.length ? `<div class="og-mem">${reste.map(escadrePiloteHtml).join("")}</div>` : ""}
      <div class="og-n">${escapeHtml(pilotesN(ms.length))}</div>
    </div>`;
  };
  const colLibres = libres.length ? `<div class="og-col og-free">
      <div class="og-sq"><div class="og-sqt"><b>${escapeHtml(t("escadre_free"))}</b><span class="og-ac">${escapeHtml(t("escadre_free_sub"))}</span></div></div>
      <div class="og-mem">${libres.map(escadrePiloteHtml).join("")}</div>
    </div>` : "";
  const organigramme = `<div class="framed">
    <div class="sec ink">${escapeHtml(t("escadre_org_title"))}</div>
    <div class="og">
      <div class="og-top"><img src="${wingEmblemSrc()}" alt="" data-wing-emblem><b>${escapeHtml(designation)}</b><span class="og-n">${escapeHtml(activesN)} · ${escapeHtml(pilotesN(effectif))}</span></div>
      <div class="og-rail">${actives.map(branche).join("")}${colLibres}</div>
    </div>
  </div>`;

  // Lot « Les cartes DCS de chaque pilote » : la synthèse. Un groupe par escadrille active, puis les
  // sans-escadrille ; les colonnes sont les cartes, de la plus déclarée de l'escadre à la moins déclarée
  // (à égalité, l'ordre de MAPS) ; une ligne d'escadrille se déplie en une ligne par pilote.
  const groupes = actives.map(sq => ({cle: String(sq.id), nom: sq.designation, membres: sq.members || []}));
  if(libres.length) groupes.push({cle: "libres", nom: t("escadre_free"), membres: libres});
  const declare = m => m.cartes_dcs != null;
  const compte = (ms, c) => ms.filter(m => declare(m) && m.cartes_dcs.includes(c)).length;
  const tous = groupes.flatMap(g => g.membres);
  const colonnes = MAPS.map((c, i) => ({c, i, n: compte(tous, c)})).sort((a, b) => (b.n - a.n) || (a.i - b.i)).map(x => x.c);
  const nb = n => n ? String(n) : `<span class="cd-zero">0</span>`;
  const entete = colonnes.map(c => `<th scope="col" title="${escapeAttr(c)}"><span class="cd-col-code">${escapeHtml(CARTES_CODES[c])}</span><span class="cd-col-nom">${escapeHtml(c)}</span></th>`).join("");
  const lignes = groupes.map(g => {
    const ouverte = cdLignesOuvertes.has(g.cle);
    const tete = `<tr class="cd-sqrow${ouverte ? " ouverte" : ""}" data-cd-sq="${escapeAttr(g.cle)}" role="button" tabindex="0" aria-expanded="${ouverte}"><th scope="row"><span class="cd-chev" aria-hidden="true">${ouverte ? "▾" : "▸"}</span>${escapeHtml(g.nom)}<span class="cd-sq-n">${g.membres.filter(declare).length}/${g.membres.length}</span></th>${colonnes.map(c => `<td>${nb(compte(g.membres, c))}</td>`).join("")}</tr>`;
    if(!ouverte) return tete;
    return tete + g.membres.map(m => declare(m)
      ? `<tr class="cd-pil"><th scope="row">${escapeHtml(callsign(m.name))}</th>${colonnes.map(c => m.cartes_dcs.includes(c) ? `<td><span class="cd-coche" aria-label="${escapeAttr(t("cd_possedee"))}">✓</span></td>` : "<td></td>").join("")}</tr>`
      : `<tr class="cd-pil cd-nd"><th scope="row">${escapeHtml(callsign(m.name))}</th><td colspan="${colonnes.length}" class="cd-nd-t">${escapeHtml(t("cd_non_declare"))}</td></tr>`
    ).join("");
  }).join("");
  const pied = `<tr class="cd-total"><th scope="row">${escapeHtml(t("cd_escadre"))}<span class="cd-sq-n">${tous.filter(declare).length}/${tous.length}</span></th>${colonnes.map(c => `<td>${nb(compte(tous, c))}</td>`).join("")}</tr>`;
  const cartes = `<div class="framed"><div class="sec ink">${escapeHtml(t("cd_escadre_titre"))}</div><div class="cd-defile"><table class="cd-tab"><thead><tr><th scope="col" class="cd-coin">${escapeHtml(t("cd_pilote"))}</th>${entete}</tr></thead><tbody>${lignes}</tbody><tfoot>${pied}</tfoot></table></div></div>`;

  return idbar + etat + orbat + organigramme + cartes;
}

// Lot « Les cartes DCS de chaque pilote » : une ligne d'escadrille du tableau se déplie et se replie, au clic
// et à Entrée quand elle a le focus.
function cdBasculeLigne(ligne, auClavier){
  const cle = ligne.dataset.cdSq;
  if(cdLignesOuvertes.has(cle)) cdLignesOuvertes.delete(cle); else cdLignesOuvertes.add(cle);
  renderEscadre();
  // Addendum 1 (A3) : la bascule au clavier rend le focus à la ligne, de même clé, après le rendu.
  if(auClavier){ const l = Array.from(document.querySelectorAll("[data-cd-sq]")).find(x => x.dataset.cdSq === cle); if(l) l.focus(); }
}
document.addEventListener("click", e => {
  const ligne = e.target.closest && e.target.closest("[data-cd-sq]");
  if(ligne) cdBasculeLigne(ligne);
});
document.addEventListener("keydown", e => {
  if(e.key !== "Enter") return;
  const ligne = e.target.closest && e.target.closest("[data-cd-sq]");
  if(ligne){ e.preventDefault(); cdBasculeLigne(ligne, true); }
});

/* ===================================================================
   Lot 3.2b « La coquille » — Centre de Commandement, écran Escadrilles.
   Un seul domaine servi (Escadrilles) ; fonction de rendu propre au
   module, jamais renderDebrief() (cf. brief Volet 2). Le CC n'a pas de
   pile de navigation à ce lot -- pas d'équivalent de debriefStack ici.
   =================================================================== */
let commandSquadronsLoadState = "idle"; // idle | loading | ready | error
let commandSquadronsError = null;
let COMMAND_SQUADRONS = null;
let COMMAND_SQUADRONS_YOU = null;     // {is_admin, squadron_id, role} -- GET /squadrons (§7.3)
let commandSquadronsEditId = null;    // id de l'escadrille en édition, ou null
let commandSquadronsEditDesig = "";
let commandSquadronsEditCallsign = "";   // lot « L'identité de l'escadrille »
let commandSquadronsEditFull = "";
let commandSquadronsEditAircraft = [];         // les appareils choisis, lot « L'appareil de l'escadrille »
let commandSquadronsEditAircraftOther = null;  // null = champ « Autre » fermé ; sinon, le texte en cours
// Lot « La config d'escadre de Mission Plan fabriquée par le Centre » (v1.0091) : le surnom et les livrées de
// l'escadrille en édition, l'erreur de sa ligne de livrée ({i, texte} ou null), et la table des appareils
// (`/static/dcs_types_livrees.json`, chargée une fois : codes du Centre -> types DCS, livrées du jeu par type).
let commandSquadronsEditNickname = "";
let commandSquadronsEditLiveries = [];         // [{name, aircraft:[appareils], jeu:bool}]
let commandSquadronsEditDefaults = {};         // {appareil: nom}
let commandSquadronsLivErr = null;
let COMMAND_DCS_TABLE = null;                  // {types, livrees} ; {echec:true} si le fichier n'a pas pu être lu
let commandSquadronsEditRole = null;
let commandSquadronsArmed = null;     // {id, gesture:"sleep"|"wake"|"crest", ...} ou null -- cf. Lot
                                       // 3.2e volet ② pour la forme du geste "crest"
let commandSquadronsNewRole = null;   // rôle choisi dans le bloc de création, avant soumission

// Chargeur partagé du catalogue des rôles Discord (Lot 3.2e §7.3) --
// aujourd'hui `COMMAND_DISCORD_ROLES` n'était peuplé que par
// `loadCommandRights()` ; Escadrilles est pourtant l'onglet actif par
// défaut du module. `GET /command/discord-roles` NE LÈVE JAMAIS (cache
// 5 min côté serveur, dernière valeur bonne) -- aucune précaution
// particulière ici, le `catch` n'est qu'un filet. Gardé sur son propre
// état de chargement : appelé par Escadrilles ET Droits, jamais deux
// requêtes pour la même chose (P21).
let commandDiscordRolesLoadState = "idle"; // idle | loading | ready
let commandDiscordRolesPromise = null;     // promesse EN VOL -- retournée telle
                                            // quelle tant que l'état vaut "loading",
                                            // pour que tout appelant reprenne la main
                                            // seulement une fois COMMAND_DISCORD_ROLES
                                            // réellement peuplé (correctif P21, geste 2).

async function ensureCommandDiscordRolesLoaded(){
  if(commandDiscordRolesLoadState === "ready"){
    return;
  }
  if(commandDiscordRolesLoadState === "loading"){
    return commandDiscordRolesPromise;
  }
  commandDiscordRolesLoadState = "loading";
  commandDiscordRolesPromise = (async ()=>{
    try {
      COMMAND_DISCORD_ROLES = await apiFetch("/api/command/discord-roles");
    } catch(e){
      COMMAND_DISCORD_ROLES = COMMAND_DISCORD_ROLES || {roles: [], available: false};
    }
    commandDiscordRolesLoadState = "ready";
  })();
  return commandDiscordRolesPromise;
}

// La table des appareils : lue une fois, au premier rendu de l'onglet. En échec, « + Livrée du jeu » est absent, les
// listes du jeu sont vides, et tout appareil déclaré est traité comme ayant un type (le reste marche).
// v1.0098 : la table se charge avec le ?v= de app.js (la version servie), en cache durable par version : un
// déploiement donne une table fraîche à tous les navigateurs.
async function ensureCommandDcsTable(){
  if(COMMAND_DCS_TABLE) return;
  try {
    // Lot « table des livrées versionnée » : la version est le ?v= de l'élément <script> qui charge app.js ;
    // sans cet élément ou sans ce paramètre, l'adresse sans ?v= d'avant.
    let urlTable = "/static/dcs_types_livrees.json";
    const scriptApp = Array.from(document.getElementsByTagName("script")).find(function(el){
      return /\/static\/app\.js(\?|$)/.test(el.getAttribute("src") || "");
    });
    if(scriptApp){
      const vApp = new URL(scriptApp.src, location.href).searchParams.get("v");
      if(vApp) urlTable += "?v=" + encodeURIComponent(vApp);
    }
    const res = await fetch(urlTable, {credentials:"same-origin"});
    const j = res.ok ? await res.json() : null;
    COMMAND_DCS_TABLE = (j && j.types && j.livrees) ? {types: j.types, livrees: j.livrees} : {echec: true};
  } catch(e){
    COMMAND_DCS_TABLE = {echec: true};
  }
}

async function loadCommandSquadrons(){
  commandSquadronsLoadState = "loading";
  commandSquadronsError = null;
  renderCommandSquadrons();
  try {
    const data = await apiFetch("/api/command/squadrons");
    COMMAND_SQUADRONS = data.squadrons || [];
    COMMAND_SQUADRONS_YOU = data.you || null;
    await ensureCommandDcsTable();
    commandSquadronsLoadState = "ready";
  } catch(e){
    commandSquadronsLoadState = "error";
    commandSquadronsError = e.message || t("error_generic");
  }
  renderCommandSquadrons();
}

function ensureCommandSquadronsLoaded(){
  if(commandSquadronsLoadState === "ready" || commandSquadronsLoadState === "loading"){
    renderCommandSquadrons();
  } else {
    loadCommandSquadrons();
  }
  // Le catalogue des rôles peut arriver APRÈS le dessin du tableau
  // (escadrilles déjà en cache, catalogue jamais encore demandé) --
  // sans ce redessin les noms n'apparaîtraient qu'à la visite suivante.
  ensureCommandDiscordRolesLoaded().then(()=>{
    if(commandSquadronsLoadState === "ready") renderCommandSquadrons();
  });
}

// Squelette de chargement (dette 15, §7.3 -- SOLDÉE au Lot 3.3, §6 : les
// deux derniers foyers de `.skel-row`, écrans Membres et Droits, sont
// retirés) : cinq largeurs DISTINCTES -- gabarit réel des cinq colonnes,
// jamais une largeur uniforme répétée. `.skel-row` retiré : la classe
// n'a jamais porté aucune règle d'apparence (cf. cssrules.py, aucune
// occurrence dans styles.css) -- son retrait ici coûte zéro règle.
function commandSquadronsSkeletonRowsHtml(){
  const widths = ["60%","40%","30%","55%","45%"];
  const row = `<tr>${widths.map(w=>`<td><span class="skel" style="width:${w}"></span></td>`).join("")}</tr>`;
  return row.repeat(4);
}

// Cellule du rôle Discord -- passe par `ccRoleName()`, qui porte déjà le
// bon repli (identifiant + mention d'absence). La mention d'absence est
// enveloppée dans <span class="absent"> (§7.1, R15 de l'inventaire CSS) ;
// le test de connaissance du rôle est celui déjà interne à `ccRoleName()`,
// répété ici seulement pour décider de l'enveloppe, jamais pour recomposer
// le texte lui-même.
function commandSquadronRoleReadHtml(sq){
  if(!sq.discord_role_id) return "—";
  const known = COMMAND_DISCORD_ROLES && (COMMAND_DISCORD_ROLES.roles||[]).some(r=>String(r.id)===String(sq.discord_role_id));
  if(known) return escapeHtml(ccRoleName(sq.discord_role_id));
  return `${escapeHtml(sq.discord_role_id)} <span class="absent">${escapeHtml(t("cc_rights_role_absent"))}</span>`;
}

// Autorité d'édition (désignation/indicatif) -- miroir d'affichage de
// `can_admin_squadron()` (app/capabilities.py) : le serveur reste seul
// juge à l'écriture, ce test ne sert qu'à proposer ou non le bouton
// Modifier (§Volet C : « ce qui est réservé à l'administrateur est
// absent, jamais grisé »).
function commandSquadronsCanEdit(sq){
  const you = COMMAND_SQUADRONS_YOU;
  if(!you) return false;
  if(you.is_admin) return true;
  return you.squadron_id === sq.id && (you.role === "leader" || you.role === "deputy");
}

// Écusson en ligne, avant le nom (Lot 3.2e, volet ②, §8.3) -- MÊME
// GABARIT exactement que l'escadrille en porte un ou non (R16/R17,
// cssrules.py) : la colonne ne bouge pas. `crest_sha` dans la query
// string casse le cache du navigateur au remplacement (§5.2) -- c'est le
// SEUL rôle de ce paramètre, le serveur ne le lit jamais.
function commandSquadronCrestHtml(sq){
  if(sq.crest_sha){
    const src = `/api/squadrons/${sq.id}/crest?v=${encodeURIComponent(sq.crest_sha)}`;
    const alt = t("cc_sqn_crest_alt").replace("{squadron}", sq.designation);
    return `<img class="sqn-crest" src="${src}" alt="${escapeAttr(alt)}">`;
  }
  return `<span class="sqn-crest empty" role="img" aria-label="${escapeAttr(t("cc_sqn_crest_none"))}"></span>`;
}

// Lot « L'appareil de l'escadrille » -- les appareils qu'une escadrille déclare
// au Centre : quatre au plus (le serveur tient la même limite), choisis dans
// AIRCRAFT_CODES -- la liste officielle de l'application, celle des préférences
// de participation -- ou saisis en « Autre… ». En lecture, reliés par un point
// médian sous la désignation ; en édition, des pastilles (.chip-picker-chip,
// le mobilier des préférences) et un menu natif pour en ajouter.
const COMMAND_SQUADRON_AIRCRAFT_MAX = 4;

function commandSquadronAircraftText(sq){
  return (sq.aircraft || []).join(" · ");
}

function commandSquadronsAddAircraft(nom){
  const n = String(nom || "").trim();
  const deja = commandSquadronsEditAircraft.some(a => a.toLowerCase() === n.toLowerCase());
  if(n && !deja && commandSquadronsEditAircraft.length < COMMAND_SQUADRON_AIRCRAFT_MAX){
    commandSquadronsEditAircraft = commandSquadronsEditAircraft.concat([n]);
  }
  commandSquadronsEditAircraftOther = null;
  renderCommandSquadrons();
}

function commandSquadronAircraftEditHtml(sq){
  const choisis = commandSquadronsEditAircraft;
  const pastilles = choisis.map(n => `<span class="chip-picker-chip">${escapeHtml(n)}<button type="button" class="chip-picker-chip-remove" data-act="ac-remove" data-id="${sq.id}" data-name="${escapeAttr(n)}" aria-label="${escapeAttr(t("cc_rights_chip_remove"))}">×</button></span>`).join("");
  let ajout = "";
  if(choisis.length < COMMAND_SQUADRON_AIRCRAFT_MAX){
    if(commandSquadronsEditAircraftOther != null){
      ajout = `<input class="cc-set" data-act="ac-other" type="text" size="12" maxlength="40" value="${escapeAttr(commandSquadronsEditAircraftOther)}" placeholder="${escapeAttr(t("cc_sqn_aircraft_other_ph"))}" aria-label="${escapeAttr(t("cc_sqn_aircraft_other_ph"))}"><button type="button" class="btn btn-sm cc-act" data-act="ac-other-ok" data-id="${sq.id}">${escapeHtml(t("cc_sqn_aircraft_other_ok"))}</button>`;
    } else {
      const deja = new Set(choisis.map(n => n.toLowerCase()));
      const options = AIRCRAFT_CODES.filter(c => !deja.has(c.toLowerCase())).map(c => `<option value="${escapeAttr(c)}">${escapeHtml(c)}</option>`).join("");
      ajout = `<select class="cc-set" data-act="ac-add" aria-label="${escapeAttr(t("cc_sqn_aircraft"))}"><option value="">${escapeHtml(t("cc_sqn_aircraft_add"))}</option>${options}<option value="__autre__">${escapeHtml(t("cc_sqn_aircraft_other"))}</option></select>`;
    }
  }
  return `<span class="sqn-ac-edit">${pastilles}${ajout}</span>`;
}

// Lot « La config d'escadre de Mission Plan fabriquée par le Centre » -- les types DCS d'un appareil de l'escadrille
// (la règle du serveur, `app/wing_config.py`) : un code de la table donne ses types (aucun pour JTAC et LotATC) ; un
// appareil hors de la table passe tel quel ; table illisible, tout appareil est son propre type.
function commandDcsTypes(code){
  const c = String(code || "").trim();
  if(!c) return [];
  const tb = COMMAND_DCS_TABLE;
  if(!tb || tb.echec) return [c];
  const k = c.toLowerCase();
  const hit = Object.keys(tb.types).find(x => x.toLowerCase() === k);
  return hit ? tb.types[hit] : [c];
}
// La liste du jeu des types d'un appareil, réunie sans doublon, triée.
function commandDcsJeuDe(code){
  const tb = COMMAND_DCS_TABLE;
  if(!tb || tb.echec) return [];
  const tous = [].concat(...commandDcsTypes(code).map(ty => tb.livrees[ty] || []));
  return Array.from(new Set(tous)).sort((a, b) => a.localeCompare(b));
}
// Les appareils de l'escadrille en édition qui ont un type DCS, et ceux qui n'en ont pas.
function commandSquadronsLivCodes(){ return commandSquadronsEditAircraft.filter(c => commandDcsTypes(c).length); }

// En lecture : « {n} livrées · {m} par défaut » (une partie à zéro disparaît), puis une ligne par livrée par défaut
// écartée -- la règle 10 de la config, vue de l'écran : une escadrille active à callsign d'`id` plus petit donne déjà
// une livrée par défaut à l'un des types DCS de l'appareil.
function commandSquadronLivResume(sq){
  const n = (sq.liveries || []).length, m = Object.keys(sq.default_liveries || {}).length;
  const p = [];
  if(n) p.push(n === 1 ? t("cc_sqn_liv_res_1") : t("cc_sqn_liv_res_n").split("{n}").join(String(n)));
  if(m) p.push(m === 1 ? t("cc_sqn_liv_res_def_1") : t("cc_sqn_liv_res_def_n").split("{n}").join(String(m)));
  return p.join(" · ");
}
function commandSquadronLivEcartees(sq){
  const avecCallsign = o => o.status === "actif" && (o.callsign || "").trim();
  if(!avecCallsign(sq)) return [];
  const avant = (COMMAND_SQUADRONS || []).filter(o => avecCallsign(o) && o.id < sq.id).sort((a, b) => a.id - b.id);
  const lignes = [];
  Object.keys(sq.default_liveries || {}).forEach(code => {
    const types = commandDcsTypes(code);
    const gagnant = avant.find(o => Object.keys(o.default_liveries || {}).some(c => commandDcsTypes(c).some(ty => types.includes(ty))));
    if(gagnant) lignes.push(t("cc_sqn_liv_ecartee").split("{aircraft}").join(code).split("{squadron}").join(gagnant.designation));
  });
  return lignes;
}

// Un nom de livrée est « offert » pour un appareil quand une livrée de la ligne le porte pour cet appareil, ou que la
// liste du jeu de ses types le contient : seule la livrée par défaut qui le nomme peut alors le garder.
function commandSquadronLivOffert(code, nom){
  if(!nom) return false;
  const bas = nom.trim().toLowerCase();
  return commandSquadronsEditLiveries.some(l => l.aircraft.includes(code) && String(l.name || "").trim().toLowerCase() === bas)
    || commandDcsJeuDe(code).includes(nom);
}
// Les gestes de livrée font suivre la livrée par défaut qui nommait `ancien` pour `code` : `nouveau` si elle est
// renommée (une custom), sinon elle part quand le nom n'est plus offert. Rien ne se normalise au rendu : seuls les
// gestes passent ici.
function commandSquadronLivSuivre(code, ancien, nouveau){
  if(!ancien || commandSquadronsEditDefaults[code] !== ancien) return;
  if(nouveau) commandSquadronsEditDefaults[code] = nouveau;
  else if(!commandSquadronLivOffert(code, ancien)) delete commandSquadronsEditDefaults[code];
}

function commandSquadronLivDefautsHtml(){
  const codes = commandSquadronsLivCodes();
  const sansType = commandSquadronsEditAircraft.filter(c => !commandDcsTypes(c).length);
  const lignes = codes.map(c => {
    const types = commandDcsTypes(c);
    const esc = Array.from(new Set(commandSquadronsEditLiveries.filter(l => String(l.name || "").trim() && l.aircraft.includes(c)).map(l => l.name.trim())));
    const cur = commandSquadronsEditDefaults[c] || "";
    const jeu = commandDcsJeuDe(c).filter(n => !esc.includes(n));
    const opt = n => `<option value="${escapeAttr(n)}"${n === cur ? " selected" : ""}>${escapeHtml(n)}</option>`;
    const aria = t("cc_sqn_liv_defaut_aria").split("{aircraft}").join(c);
    const sel = `<select class="cc-set sqn-liv-def-choix" data-act="liv-def" data-code="${escapeAttr(c)}" aria-label="${escapeAttr(aria)}">` +
      `<option value=""${cur ? "" : " selected"}>${escapeHtml(t("cc_sqn_liv_defaut_aucune"))}</option>` +
      (esc.length ? `<optgroup label="${escapeAttr(t("cc_sqn_liv_defaut_esc"))}">${esc.map(opt).join("")}</optgroup>` : "") +
      (jeu.length ? `<optgroup label="${escapeAttr(t("cc_sqn_liv_defaut_jeu"))}">${jeu.map(opt).join("")}</optgroup>` : "") + `</select>`;
    const plus = types.length > 1 ? `<span class="sqn-liv-types">${escapeHtml(t("cc_sqn_liv_types").split("{n}").join(String(types.length)))}</span>` : "";
    return `<li class="sqn-liv-def"><span class="sqn-liv-code">${escapeHtml(c)}${plus}</span>${sel}</li>`;
  }).join("");
  const sans = sansType.length ? `<p class="sqn-liv-aide">${escapeHtml(t("cc_sqn_liv_sans").split("{aircraft}").join(sansType.join(", ")))}</p>` : "";
  return (codes.length ? `<ul class="sqn-liv-liste">${lignes}</ul>` : `<p class="sqn-liv-aide">${escapeHtml(t("cc_sqn_liv_sans_appareil"))}</p>`) + sans;
}

function commandSquadronLivBlocHtml(){
  const codes = commandSquadronsLivCodes();
  const codesJeu = codes.filter(c => commandDcsJeuDe(c).length);
  const err = commandSquadronsLivErr;
  const lignes = commandSquadronsEditLiveries.map((l, i) => {
    const errL = err && err.i === i ? `<div class="sqn-liv-err" role="alert">${escapeHtml(err.texte)}</div>` : "";
    const retirer = `<button type="button" class="btn btn-sm cc-act sqn-liv-retirer" data-act="liv-retirer" data-i="${i}" aria-label="${escapeAttr(t("cc_sqn_liv_retirer_aria"))}">${escapeHtml(t("cc_sqn_liv_retirer"))}</button>`;
    if(l.jeu){
      // Une livrée du jeu dont l'appareil n'est plus déclaré reste telle quelle (appareil vide) : erreur à « Enregistrer ».
      const c = l.aircraft[0] || "";
      const selAc = (codesJeu.length > 1 || (!c && codesJeu.length))
        ? `<select class="cc-set" data-act="liv-jeu-ac" data-i="${i}" aria-label="${escapeAttr(t("cc_sqn_liv_jeu_appareil_aria"))}">${c ? "" : '<option value="" selected>—</option>'}${codesJeu.map(x => `<option${x === c ? " selected" : ""}>${escapeHtml(x)}</option>`).join("")}</select>`
        : `<span class="sqn-liv-puce on fixe">${escapeHtml(c)}</span>`;
      const liste = commandDcsJeuDe(c);
      if(l.name && !liste.includes(l.name)) liste.push(l.name);
      const selNom = `<select class="cc-set sqn-liv-nom" data-act="liv-jeu-nom" data-i="${i}" aria-label="${escapeAttr(t("cc_sqn_liv_jeu_aria"))}"><option value="">${escapeHtml(t("cc_sqn_liv_jeu_choisir"))}</option>${liste.map(n => `<option${n === l.name ? " selected" : ""}>${escapeHtml(n)}</option>`).join("")}</select>`;
      return `<li class="sqn-liv-ligne"><span class="sqn-liv-tag">${escapeHtml(t("cc_sqn_liv_tag_jeu"))}</span>${selNom}${selAc}${retirer}${errL}</li>`;
    }
    const puces = codes.map(c => {
      const on = l.aircraft.includes(c);
      return `<button type="button" class="sqn-liv-puce${on ? " on" : ""}" aria-pressed="${on}" data-act="liv-puce" data-i="${i}" data-code="${escapeAttr(c)}">${escapeHtml(c)}</button>`;
    }).join("");
    return `<li class="sqn-liv-ligne"><span class="sqn-liv-tag custom">${escapeHtml(t("cc_sqn_liv_tag_custom"))}</span>` +
      `<input class="cc-set sqn-liv-nom" type="text" maxlength="80" value="${escapeAttr(l.name)}" data-act="liv-nom" data-i="${i}" placeholder="${escapeAttr(t("cc_sqn_liv_nom_ph"))}" aria-label="${escapeAttr(t("cc_sqn_liv_nom_aria"))}">` +
      `<span class="sqn-liv-puces" role="group">${puces}</span>${retirer}${errL}</li>`;
  }).join("");
  const ajoutJeu = codesJeu.length ? `<button type="button" class="btn btn-sm cc-act" data-act="liv-ajouter-jeu">${escapeHtml(t("cc_sqn_liv_ajout_jeu"))}</button>` : "";
  return `<div class="sqn-liv-bloc"><div class="sqn-liv-cols">` +
    `<section class="sqn-liv-sec"><h4>${escapeHtml(t("cc_sqn_liv_titre"))}</h4>` +
      (commandSquadronsEditLiveries.length ? `<ul class="sqn-liv-liste">${lignes}</ul>` : `<p class="sqn-liv-aide">${escapeHtml(t("cc_sqn_liv_aucune"))}</p>`) +
      `<div class="sqn-liv-ajouts">${ajoutJeu}<button type="button" class="btn btn-sm cc-act" data-act="liv-ajouter-custom">${escapeHtml(t("cc_sqn_liv_ajout_custom"))}</button></div>` +
      `<p class="sqn-liv-aide">${escapeHtml(t("cc_sqn_liv_aide"))}</p></section>` +
    `<section class="sqn-liv-sec"><h4>${escapeHtml(t("cc_sqn_liv_defaut_titre"))}</h4><div data-zone="liv-defauts">${commandSquadronLivDefautsHtml()}</div></section>` +
    `</div></div>`;
}

function commandSquadronRowHtml(sq){
  const statusKey = sq.status === "actif" ? "cc_sqn_status_actif" : "cc_sqn_status_sommeil";
  const you = COMMAND_SQUADRONS_YOU || {is_admin: false};
  const editing = commandSquadronsEditId === sq.id;
  const armed = (commandSquadronsArmed && commandSquadronsArmed.id === sq.id) ? commandSquadronsArmed : null;

  let cDesig, cCall, cFull, cRole, cAct;

  if(editing){
    cDesig = `<span class="sqn-cell">${commandSquadronCrestHtml(sq)}<span class="sqn-id"><input class="cc-set" data-act="ed-desig" type="text" maxlength="24" size="14" value="${escapeAttr(commandSquadronsEditDesig)}" aria-label="${escapeAttr(t("cc_sqn_col_designation"))}">${commandSquadronAircraftEditHtml(sq)}</span></span>`;
    cCall  = `<input class="cc-set" data-act="ed-callsign" type="text" maxlength="32" size="10" value="${escapeAttr(commandSquadronsEditCallsign)}" aria-label="${escapeAttr(t("cc_sqn_col_callsign"))}">`;
    cFull  = `<span class="sqn-full-edit"><input class="cc-set" data-act="ed-full" type="text" maxlength="100" size="22" value="${escapeAttr(commandSquadronsEditFull)}" aria-label="${escapeAttr(t("cc_sqn_col_fullname"))}">` +
      `<input class="cc-set" data-act="ed-nickname" type="text" size="22" maxlength="60" value="${escapeAttr(commandSquadronsEditNickname)}" placeholder="${escapeAttr(t("cc_sqn_nickname"))}" aria-label="${escapeAttr(t("cc_sqn_nickname"))}"></span>`;
    cRole  = you.is_admin ? ccRoleSelectHtml(commandSquadronsEditRole, "ed-role") : commandSquadronRoleReadHtml(sq);
    cAct   = `<div class="cc-row">
      <button type="button" class="btn btn-sm cc-act" data-act="sqn-save" data-id="${sq.id}">${escapeHtml(t("cc_sqn_act_save"))}</button>
      <button type="button" class="btn btn-sm cc-act" data-act="sqn-cancel" data-id="${sq.id}">${escapeHtml(t("cc_rights_cancel"))}</button>
    </div>`;
  } else {
    const avions = commandSquadronAircraftText(sq);
    const resume = commandSquadronLivResume(sq);
    const ecartees = commandSquadronLivEcartees(sq).map(x => `<span class="sqn-liv-ecartee">${escapeHtml(x)}</span>`).join("");
    cDesig = `<span class="sqn-cell">${commandSquadronCrestHtml(sq)}<span class="sqn-id">${escapeHtml(sq.designation)}${avions ? `<span class="sqn-ac">${escapeHtml(avions)}</span>` : ""}${resume ? `<span class="sqn-liv-res">${escapeHtml(resume)}</span>` : ""}${ecartees}</span></span>`;
    // Lot « L'identité de l'escadrille » : une valeur vide s'estompe.
    cCall  = sq.callsign ? escapeHtml(sq.callsign) : `<span class="vide">—</span>`;
    cFull  = (sq.full_name ? escapeHtml(sq.full_name) : `<span class="vide">—</span>`) +
      (sq.nickname ? `<span class="sqn-surnom">«\u00a0${escapeHtml(sq.nickname)}\u00a0»</span>` : "");
    cRole  = commandSquadronRoleReadHtml(sq);
    const b = [];
    if(commandSquadronsCanEdit(sq)){
      b.push(`<button type="button" class="btn btn-sm cc-act" data-act="sqn-edit" data-id="${sq.id}">${escapeHtml(t("cc_sqn_act_edit"))}</button>`);
      // Sélecteur de fichier -- patron de la maquette, repris tel quel
      // (§8.3) : <label class="btn btn-sm cc-act"> enveloppant un
      // <input type="file" class="hidden">. `.btn` est un sélecteur de
      // CLASSE, il s'applique au label et porte déjà cursor:pointer --
      // AUCUN habillage de input[type=file], dont le rendu natif est
      // incontrôlable d'un navigateur à l'autre. Coût : zéro règle.
      b.push(`<label class="btn btn-sm cc-act">${escapeHtml(t("cc_sqn_act_crest"))}<input type="file" class="hidden" accept="image/png,image/webp" data-act="crest-pick" data-id="${sq.id}"></label>`);
    }
    if(you.is_admin){
      if(sq.status === "actif"){
        b.push(`<button type="button" class="btn btn-sm cc-act${armed && armed.gesture==="sleep" ? " arm" : ""}" data-act="sqn-sleep" data-id="${sq.id}">${escapeHtml(t("cc_sqn_act_sleep"))}</button>`);
      } else {
        b.push(`<button type="button" class="btn btn-sm cc-act${armed && armed.gesture==="wake" ? " arm" : ""}" data-act="sqn-wake" data-id="${sq.id}">${escapeHtml(t("cc_sqn_act_wake"))}</button>`);
      }
    }
    cAct = b.length ? `<div class="cc-row">${b.join("")}</div>` : "";
  }

  // En édition, la ligne garde ses champs et une ligne la suit : le bloc des livrées (`.sqn-liv-bloc`).
  return `<tr${editing ? ' class="sqn-liv-edition"' : ""}>
    <td>${cDesig}</td>
    <td class="sqn-tag">${cCall}</td>
    <td class="sqn-full">${cFull}</td>
    <td><span class="sqn-status ${escapeHtml(sq.status)}">${escapeHtml(t(statusKey))}</span></td>
    <td class="sqn-role">${cRole}</td>
    <td>${cAct}</td>
  </tr>` + (editing ? `<tr class="sqn-liv-suite"><td colspan="6">${commandSquadronLivBlocHtml()}</td></tr>` : "");
}

// Définition retenue (décidée par le CdP le 16 août, cf. brief §4) :
// partiel = au moins une escadrille actif dont discord_role_id est NULL.
function commandSquadronsIsPartial(list){
  return list.some(sq => sq.status === "actif" && !sq.discord_role_id);
}

// Ligne de conséquence -- affichée PENDANT la saisie (renommage/indicatif,
// avant d'enregistrer) ou pour l'armement Endormir/Réveiller (patron :
// écran Droits, `showCommandRightsNote`/`#cc-note-zone`, mais mobilier
// propre à cet écran -- pas de confirmation réseau avant clic explicite).
// Lot « Le Centre au doigt et à la charte » (v1.0081, R617) : la forme commune (`.rr-confirm`) des confirmations du
// Centre, qui gardent leur mécanique (gestes armés, zones de note). `texte` est du HTML déjà sûr ; `err` est un texte
// brut (le refus du serveur reste dans la note) ; « Annuler » avant l'action, rouge quand l'action retire.
function ccConfirmHtml({titre, texte, choix = "", err = null, danger = false, annuler, ok, libelle, attrs = "", occupe = false}){
  // Addendum 1 : une note dont l'action court est dessinée occupée -- ses deux boutons et son `select` sont `disabled`.
  const dis = occupe ? " disabled" : "";
  if(occupe) choix = choix.replace(/<select /g, "<select disabled ");
  return `<div class="rr-confirm${danger ? " danger" : ""}" role="group" aria-label="${escapeAttr(titre)}">` +
    `<div class="rr-confirm-titre">${escapeHtml(titre)}</div>` +
    `<div class="rr-confirm-texte">${texte}</div>${choix}` +
    `<div class="rr-confirm-err" role="alert"${err ? "" : " hidden"}>${err ? escapeHtml(err) : ""}</div>` +
    `<div class="rr-confirm-actions">` +
      `<button type="button" class="btn btn-sm" data-act="${annuler}"${dis}>${escapeHtml(t("cc_rights_cancel"))}</button>` +
      `<button type="button" class="btn btn-sm ${danger ? "btn-danger" : "btn-accent"}" data-act="${ok}"${attrs}${dis}>${escapeHtml(libelle)}</button>` +
    `</div></div>`;
}
// Les boutons et le `select` de la note sont `disabled` pendant l'appel (R5, addendum 1).
function ccConfirmOccupe(bouton){
  const note = bouton && bouton.closest ? bouton.closest(".rr-confirm") : null;
  if(note) note.querySelectorAll("button, select").forEach(x=>{ x.disabled = true; });
}

function renderCommandSquadronsNote(){
  const zone = $("#cc-sqn-note-zone");
  if(!zone) return;
  zone.innerHTML = "";

  if(commandSquadronsEditId != null){
    const sq = (COMMAND_SQUADRONS||[]).find(s=>s.id===commandSquadronsEditId);
    if(!sq) return;
    const nd = commandSquadronsEditDesig.trim();
    const lignes = [];
    // Lot « L'identité de l'escadrille » : l'identifiant est aussi le
    // préfixe retiré des pseudos -- le renommer, c'est aussi changer ce
    // préfixe pour tous les noms affichés. Deux lignes, dans cet ordre.
    if(nd && nd !== sq.designation){
      lignes.push(t("cc_sqn_rename_effect").replace("{new}", escapeHtml(nd)).replace("{old}", escapeHtml(sq.designation)));
      lignes.push(t("cc_sqn_tag_effect").replace("{old}", escapeHtml(sq.designation)).replace("{new}", escapeHtml(nd)));
    }
    if(lignes.length) zone.innerHTML = lignes.map(l=>`<div class="cc-note">${l}</div>`).join("");
    return;
  }

  if(!commandSquadronsArmed) return;
  const sq = (COMMAND_SQUADRONS||[]).find(s=>s.id===commandSquadronsArmed.id);
  if(!sq) return;

  if(commandSquadronsArmed.gesture === "sleep"){
    const m = sq.member_count || 0;
    const phrase = m > 0
      ? t("cc_sqn_sleep_confirm").replace("{squadron}", escapeHtml(sq.designation)).replace("{count}", m)
      : t("cc_sqn_sleep_confirm_empty").replace("{squadron}", escapeHtml(sq.designation));
    zone.innerHTML = ccConfirmHtml({
      titre: t("cc_sqn_sleep_titre"), texte: phrase, danger: true, err: commandSquadronsArmed.erreur || null, occupe: !!commandSquadronsArmed.enCours,
      annuler: "sqn-cancel-arm", ok: "sqn-sleep-ok", libelle: t("cc_rights_confirm_apply"),
    });
    return;
  }

  if(commandSquadronsArmed.gesture === "wake"){
    // Lot « Le Centre au doigt et à la charte » : le texte reste l'invite ; le refus (aucun rôle choisi) ou celui du
    // serveur passe dans la ligne d'erreur de la note.
    const refus = commandSquadronsArmed.refus;
    const err = refus
      ? t("cc_sqn_wake_deny").replace("{squadron}", sq.designation)
      : (commandSquadronsArmed.erreur || null);
    zone.innerHTML = ccConfirmHtml({
      titre: t("cc_sqn_wake_titre"), texte: t("cc_sqn_wake_pick").replace("{squadron}", escapeHtml(sq.designation)),
      choix: ccRoleSelectHtml(commandSquadronsArmed.roleChoisi, "sqn-wake-role"), err, occupe: !!commandSquadronsArmed.enCours,
      annuler: "sqn-cancel-arm", ok: "sqn-wake-ok", libelle: t("cc_rights_confirm_apply"),
    });
    return;
  }

  if(commandSquadronsArmed.gesture === "crest"){
    const a = commandSquadronsArmed;
    // Refus client (politesse, jamais une garantie -- le serveur revérifie
    // tout, §9/§8.3) : s'écrit en .cc-note.deny, n'efface pas l'écusson
    // déjà en place (la rangée derrière reste inchangée pendant ce temps).
    if(a.denyKey){
      const msg = t(a.denyKey).replace("{name}", escapeHtml(a.fileName)).replace("{size}", a.denySize || "");
      zone.innerHTML = `<div class="cc-note deny">${msg}
        <button type="button" class="btn btn-sm cc-act" data-act="crest-cancel-arm">${escapeHtml(t("cc_rights_cancel"))}</button></div>`;
      return;
    }
    // Aperçu pas encore prêt (FileReader/Image encore en vol) -- rien à
    // afficher tant que les dimensions source ne sont pas connues.
    if(!a.previewSrc) return;
    const dims = `${a.sourceW} × ${a.sourceH} px`;
    const previewMsg = t("cc_sqn_crest_preview").replace("{dims}", dims);
    zone.innerHTML = ccConfirmHtml({
      titre: t("cc_sqn_crest_titre"), texte: escapeHtml(previewMsg),
      choix: `<img class="sqn-crest lg" src="${escapeAttr(a.previewSrc)}" alt="${escapeAttr(t("cc_sqn_crest_alt").replace("{squadron}", sq.designation))}">`,
      err: a.erreur || null, occupe: !!a.enCours,
      annuler: "crest-cancel-arm", ok: "crest-apply", libelle: t("cc_sqn_crest_apply"),
    });
  }
}

// Bloc de création -- admin seul (§2 point 1), masqué au non-admin et
// pendant le chargement (maquette : `!ETAT.admin || ETAT.chargement`).
function renderCommandSquadronsCreate(){
  const block = $("#cc-sqn-create");
  if(!block) return;
  const you = COMMAND_SQUADRONS_YOU;
  const show = !!(you && you.is_admin) && commandSquadronsLoadState === "ready";
  block.classList.toggle("hidden", !show);
  if(show){
    const wrap = $("#cc-sqn-new-role-wrap");
    if(wrap) wrap.innerHTML = ccRoleSelectHtml(commandSquadronsNewRole, "new-role");
  }
}

function renderCommandSquadrons(){
  const table = $("#cc-sqn-table");
  const tbody = $("#cc-sqn-tbody");
  const wrap = table ? table.closest(".cc-wrap") : null;
  const emptyEl = $("#cc-sqn-empty");
  const errorEl = $("#cc-sqn-error");
  const partialEl = $("#cc-sqn-partial");
  if(!table || !tbody || !wrap || !emptyEl || !errorEl || !partialEl) return;

  wrap.classList.add("hidden");
  emptyEl.classList.add("hidden");
  errorEl.classList.add("hidden");
  partialEl.classList.add("hidden");

  if(commandSquadronsLoadState === "loading"){
    wrap.classList.remove("hidden");
    tbody.innerHTML = commandSquadronsSkeletonRowsHtml();
    ccStampLabels();
    renderCommandSquadronsCreate();
    return;
  }
  if(commandSquadronsLoadState === "error"){
    errorEl.classList.remove("hidden");
    renderCommandSquadronsCreate();
    return;
  }
  const list = COMMAND_SQUADRONS || [];
  if(list.length === 0){
    emptyEl.classList.remove("hidden");
    renderCommandSquadronsCreate();
    return;
  }
  wrap.classList.remove("hidden");
  tbody.innerHTML = list.map(commandSquadronRowHtml).join("");
  ccStampLabels();
  wireCommandSquadronCrestFallback(tbody);
  if(commandSquadronsIsPartial(list)){
    partialEl.classList.remove("hidden");
  }
  renderCommandSquadronsNote();
  renderCommandSquadronsCreate();
}

// Filet du fichier disparu (§7.2/§8.3) : `error` sur une image d'écusson
// bascule vers l'emplacement vide, MÊME gabarit (R17), jamais une image
// cassée. `error` ne bouillonne pas (contrairement à la plupart des
// événements DOM) -- l'écouteur est donc lié directement à chaque <img>,
// après CHAQUE rendu du corps de table (le tbody est entièrement
// remplacé à chaque rendu), jamais en attribut `onerror`.
function wireCommandSquadronCrestFallback(tbody){
  tbody.querySelectorAll("img.sqn-crest").forEach(img=>{
    img.addEventListener("error", ()=>{
      img.outerHTML = `<span class="sqn-crest empty" role="img" aria-label="${escapeAttr(t("cc_sqn_crest_none"))}"></span>`;
    }, {once: true});
  });
}

// --- Appels réseau (§Volet C) ---------------------------------------

async function patchSquadron(squadronId, body){
  return apiFetch(`/api/command/squadrons/${squadronId}`, {
    method: "PATCH", headers: {"Content-Type": "application/json"},
    body: JSON.stringify(body),
  });
}

async function putSquadronSleep(squadronId){
  return apiFetch(`/api/command/squadrons/${squadronId}/sleep`, {method: "PUT"});
}

async function putSquadronWake(squadronId, discordRoleId){
  return apiFetch(`/api/command/squadrons/${squadronId}/wake`, {
    method: "PUT", headers: {"Content-Type": "application/json"},
    body: JSON.stringify({discord_role_id: discordRoleId}),
  });
}

async function postSquadron(body){
  return apiFetch("/api/command/squadrons", {
    method: "POST", headers: {"Content-Type": "application/json"},
    body: JSON.stringify(body),
  });
}

function commandSquadronsResetEdit(){
  commandSquadronsEditId = null;
  commandSquadronsEditDesig = "";
  commandSquadronsEditCallsign = "";
  commandSquadronsEditFull = "";
  commandSquadronsEditAircraft = [];
  commandSquadronsEditAircraftOther = null;
  commandSquadronsEditNickname = "";
  commandSquadronsEditLiveries = [];
  commandSquadronsEditDefaults = {};
  commandSquadronsLivErr = null;
  commandSquadronsEditRole = null;
}

// --- Geste écusson (Lot 3.2e, volet ②, §8.3) -------------------------

function crestReadFileAsDataUrl(file){
  return new Promise((resolve, reject)=>{
    const fr = new FileReader();
    fr.onload = ()=> resolve(fr.result);
    fr.onerror = ()=> reject(fr.error || new Error("read failed"));
    fr.readAsDataURL(file);
  });
}

function crestLoadImageDims(dataUrl){
  return new Promise((resolve, reject)=>{
    const im = new Image();
    im.onload = ()=> resolve({w: im.naturalWidth, h: im.naturalHeight});
    im.onerror = ()=> reject(new Error("decode failed"));
    im.src = dataUrl;
  });
}

// Sélection d'un fichier (§8.3, §9). Les trois refus du client sont une
// POLITESSE, jamais une garantie -- le serveur revérifie tout (§6). Armer
// le geste écusson annule une édition en cours (exclusion mutuelle,
// exactement comme « Modifier » et « Endormir » s'annulent déjà entre
// eux) ; `commandSquadronsArmed` étant un slot unique, il écrase aussi
// tout armement sommeil/réveil précédent.
function handleCommandSquadronCrestPick(input){
  const file = input.files && input.files[0];
  if(!file) return;
  const squadronId = Number(input.dataset.id);
  const fileName = file.name;

  commandSquadronsResetEdit();

  if(/\.svgz?$/i.test(fileName) || file.type === "image/svg+xml"){
    commandSquadronsArmed = {id: squadronId, gesture:"crest", denyKey:"cc_sqn_crest_deny_vector", fileName, previewSrc:null};
    renderCommandSquadrons();
    input.value = "";
    return;
  }
  if(file.size > 2 * 1024 * 1024){
    const denySize = (file.size / (1024 * 1024)).toFixed(1);
    commandSquadronsArmed = {id: squadronId, gesture:"crest", denyKey:"cc_sqn_crest_deny_weight", fileName, denySize, previewSrc:null};
    renderCommandSquadrons();
    input.value = "";
    return;
  }
  if(!/^image\/(png|webp)$/.test(file.type)){
    commandSquadronsArmed = {id: squadronId, gesture:"crest", denyKey:"cc_sqn_crest_deny_format", fileName, previewSrc:null};
    renderCommandSquadrons();
    input.value = "";
    return;
  }

  commandSquadronsArmed = {
    id: squadronId, gesture:"crest", denyKey:null, fileName,
    previewSrc:null, sourceW:null, sourceH:null, fileBlob:file,
  };
  renderCommandSquadrons();

  (async ()=>{
    try {
      const dataUrl = await crestReadFileAsDataUrl(file);
      const dims = await crestLoadImageDims(dataUrl);
      const a = commandSquadronsArmed;
      if(!a || a.id !== squadronId || a.gesture !== "crest" || a.fileBlob !== file) return; // annulé entretemps
      a.previewSrc = dataUrl;
      a.sourceW = dims.w;
      a.sourceH = dims.h;
      renderCommandSquadronsNote();
    } catch(err){
      const a = commandSquadronsArmed;
      if(!a || a.id !== squadronId || a.gesture !== "crest" || a.fileBlob !== file) return;
      a.denyKey = "cc_sqn_crest_deny_broken";
      a.fileName = fileName;
      renderCommandSquadronsNote();
    }
  })();

  input.value = "";
}

// Câblage des événements de l'écran Escadrilles (§7.3). Patron :
// `wireCommandRightsEvents()` -- câblage unique, `view.dataset.wired`.
function wireCommandSquadronsEvents(){
  const view = $("#view-cc-escadrilles");
  if(!view || view.dataset.wired) return;
  view.dataset.wired = "1";

  view.addEventListener("click", e=>{
    const b = e.target.closest("[data-act]");
    if(!b || b.tagName === "SELECT") return;
    const act = b.dataset.act;
    const id = b.dataset.id ? Number(b.dataset.id) : (commandSquadronsArmed ? commandSquadronsArmed.id : null);
    const sq = (COMMAND_SQUADRONS||[]).find(s=>s.id===id);

    if(act === "ac-remove"){
      commandSquadronsEditAircraft = commandSquadronsEditAircraft.filter(n => n !== b.dataset.name);
      // Lot « La config d'escadre… » : l'appareil retiré quitte chaque livrée et la livrée par défaut.
      commandSquadronsEditLiveries.forEach(l => { l.aircraft = l.aircraft.filter(n => n !== b.dataset.name); });
      delete commandSquadronsEditDefaults[b.dataset.name];
      commandSquadronsLivErr = null;
      renderCommandSquadrons();
      return;
    }
    // Lot « La config d'escadre… » : les gestes du bloc des livrées (l'état vit dans commandSquadronsEdit*).
    if(act === "liv-ajouter-custom" || act === "liv-ajouter-jeu" || act === "liv-retirer" || act === "liv-puce"){
      const codes = commandSquadronsLivCodes();
      const i = Number(b.dataset.i);
      if(act === "liv-ajouter-custom"){
        commandSquadronsEditLiveries.push({name: "", aircraft: codes.length === 1 ? codes.slice() : [], jeu: false});
      } else if(act === "liv-ajouter-jeu"){
        const avecListe = codes.filter(c => commandDcsJeuDe(c).length);
        commandSquadronsEditLiveries.push({name: "", aircraft: avecListe.slice(0, 1), jeu: true});
      } else if(act === "liv-retirer"){
        const [partie] = commandSquadronsEditLiveries.splice(i, 1);
        if(partie) partie.aircraft.forEach(c => commandSquadronLivSuivre(c, String(partie.name || "").trim(), null));
      } else if(commandSquadronsEditLiveries[i]){
        const l = commandSquadronsEditLiveries[i], c = b.dataset.code;
        const avait = l.aircraft.includes(c);
        l.aircraft = avait ? l.aircraft.filter(x => x !== c) : l.aircraft.concat([c]);
        if(avait) commandSquadronLivSuivre(c, String(l.name || "").trim(), null);
      }
      commandSquadronsLivErr = null;
      renderCommandSquadrons();
      return;
    }
    if(act === "ac-other-ok"){
      commandSquadronsAddAircraft(commandSquadronsEditAircraftOther);
      return;
    }
    if(act === "sqn-edit"){
      if(!sq) return;
      commandSquadronsArmed = null;
      commandSquadronsEditId = sq.id;
      commandSquadronsEditDesig = sq.designation;
      commandSquadronsEditCallsign = sq.callsign || "";
      commandSquadronsEditFull = sq.full_name || "";
      commandSquadronsEditAircraft = (sq.aircraft || []).slice();
      commandSquadronsEditAircraftOther = null;
      commandSquadronsEditNickname = sq.nickname || "";
      commandSquadronsEditLiveries = (sq.liveries || []).map(l => ({name: l.name, aircraft: (l.aircraft || []).slice(), jeu: !!l.jeu}));
      commandSquadronsEditDefaults = Object.assign({}, sq.default_liveries || {});
      commandSquadronsLivErr = null;
      commandSquadronsEditRole = sq.discord_role_id;
      renderCommandSquadrons();
      return;
    }
    if(act === "sqn-cancel"){
      commandSquadronsResetEdit();
      renderCommandSquadrons();
      return;
    }
    if(act === "sqn-save"){
      if(!sq) return;
      const nd = commandSquadronsEditDesig.trim();
      const nc = commandSquadronsEditCallsign.trim();
      const nf = commandSquadronsEditFull.trim();
      if(!nd){
        showToast(t("cc_sqn_create_deny_fields"), "erreur");
        return;
      }
      const you = COMMAND_SQUADRONS_YOU || {is_admin:false};
      const body = {};
      if(nd !== sq.designation) body.designation = nd;
      if(nc !== (sq.callsign || "")) body.callsign = nc || null;
      if(nf !== (sq.full_name || "")) body.full_name = nf || null;
      if(JSON.stringify(commandSquadronsEditAircraft) !== JSON.stringify(sq.aircraft || [])) body.aircraft = commandSquadronsEditAircraft.slice();
      // Lot « La config d'escadre… » : le surnom, puis les livrées -- chacune vérifiée d'abord (rien ne part s'il y a
      // une erreur) ; le PATCH ne porte `liveries` et `default_liveries` que s'ils diffèrent de l'escadrille lue.
      const nn = commandSquadronsEditNickname.trim();
      if(nn !== (sq.nickname || "")) body.nickname = nn || null;
      const livs = commandSquadronsEditLiveries.map(l => ({name: String(l.name || "").trim(), aircraft: l.aircraft.slice(), jeu: !!l.jeu}));
      const vus = [];
      for(let i = 0; i < livs.length; i++){
        const erreur = (!livs[i].name || !livs[i].aircraft.length) ? t("cc_sqn_liv_err_ligne")
          : (vus.includes(livs[i].name.toLowerCase()) ? t("cc_sqn_liv_err_double") : null);
        if(erreur){
          commandSquadronsLivErr = {i, texte: erreur};
          renderCommandSquadrons();
          return;
        }
        vus.push(livs[i].name.toLowerCase());
      }
      const defauts = {};
      Object.keys(commandSquadronsEditDefaults).forEach(c => {
        const v = String(commandSquadronsEditDefaults[c] || "").trim();
        if(v) defauts[c] = v;
      });
      const canonL = list => JSON.stringify((list || []).map(l => ({name: String(l.name || "").trim(), aircraft: l.aircraft || [], jeu: !!l.jeu})));
      const canonD = obj => JSON.stringify(Object.keys(obj || {}).sort().map(k => [k, obj[k]]));
      if(canonL(livs) !== canonL(sq.liveries)) body.liveries = livs;
      if(canonD(defauts) !== canonD(sq.default_liveries)) body.default_liveries = defauts;
      if(you.is_admin && commandSquadronsEditRole !== sq.discord_role_id){
        body.discord_role_id = commandSquadronsEditRole || null;
      }
      const savedId = sq.id;
      (async ()=>{
        try {
          await patchSquadron(savedId, body);
          commandSquadronsResetEdit();
          await loadCommandSquadrons();
        } catch(err){
          showToast(err.message || t("error_generic"), "erreur");
        }
      })();
      return;
    }
    if(act === "sqn-sleep"){
      if(!sq) return;
      commandSquadronsResetEdit();
      commandSquadronsArmed = (commandSquadronsArmed && commandSquadronsArmed.id===id && commandSquadronsArmed.gesture==="sleep")
        ? null : {id, gesture:"sleep"};
      renderCommandSquadrons();
      return;
    }
    if(act === "sqn-wake"){
      if(!sq) return;
      commandSquadronsResetEdit();
      commandSquadronsArmed = (commandSquadronsArmed && commandSquadronsArmed.id===id && commandSquadronsArmed.gesture==="wake")
        ? null : {id, gesture:"wake", roleChoisi:null, refus:false};
      renderCommandSquadrons();
      return;
    }
    if(act === "sqn-cancel-arm"){
      if(commandSquadronsArmed && commandSquadronsArmed.enCours) return; // addendum 1 : la note est occupée
      commandSquadronsArmed = null;
      renderCommandSquadrons();
      return;
    }
    if(act === "sqn-sleep-ok"){
      const armedId = commandSquadronsArmed ? commandSquadronsArmed.id : null;
      if(armedId == null) return;
      const armed = commandSquadronsArmed;
      if(armed.enCours) return;
      armed.erreur = null;
      armed.enCours = true;
      ccConfirmOccupe(b);
      (async ()=>{
        try {
          await putSquadronSleep(armedId);
          armed.enCours = false;
          commandSquadronsArmed = null;
          await loadCommandSquadrons();
        } catch(err){
          // Lot « Le Centre au doigt et à la charte » (R5) : l'état armé reste, le refus du serveur est dans la note.
          armed.enCours = false;
          armed.erreur = err.message || t("error_generic");
          if(commandSquadronsArmed === armed) renderCommandSquadrons();
        }
      })();
      return;
    }
    if(act === "sqn-wake-ok"){
      if(!commandSquadronsArmed) return;
      if(commandSquadronsArmed.enCours) return;
      if(!commandSquadronsArmed.roleChoisi){
        commandSquadronsArmed.refus = true;
        renderCommandSquadronsNote();
        return;
      }
      const armedId = commandSquadronsArmed.id;
      const roleChoisi = commandSquadronsArmed.roleChoisi;
      const armed = commandSquadronsArmed;
      armed.erreur = null;
      armed.enCours = true;
      ccConfirmOccupe(b);
      (async ()=>{
        try {
          await putSquadronWake(armedId, roleChoisi);
          armed.enCours = false;
          commandSquadronsArmed = null;
          await loadCommandSquadrons();
        } catch(err){
          armed.enCours = false;
          armed.erreur = err.message || t("error_generic");
          if(commandSquadronsArmed === armed) renderCommandSquadrons();
        }
      })();
      return;
    }
    if(act === "sqn-create"){
      const desig = ($("#cc-sqn-new-desig") ? $("#cc-sqn-new-desig").value : "").trim();
      const callsign = ($("#cc-sqn-new-callsign") ? $("#cc-sqn-new-callsign").value : "").trim();
      const fullName = ($("#cc-sqn-new-fullname") ? $("#cc-sqn-new-fullname").value : "").trim();
      const roleId = commandSquadronsNewRole;
      const noteEl = $("#cc-sqn-create-note");
      if(!desig){
        if(noteEl) noteEl.innerHTML = `<div class="cc-note deny">${escapeHtml(t("cc_sqn_create_deny_fields"))}</div>`;
        return;
      }
      const pris = (COMMAND_SQUADRONS||[]).find(s=>s.status==="actif" && s.discord_role_id && String(s.discord_role_id)===String(roleId));
      if(roleId && pris){
        if(noteEl) noteEl.innerHTML = `<div class="cc-note deny">${escapeHtml(t("cc_sqn_create_deny_role").replace("{squadron}", pris.designation))}</div>`;
        return;
      }
      (async ()=>{
        try {
          const created = await postSquadron({designation: desig, callsign: callsign || null, full_name: fullName || null, discord_role_id: roleId || null});
          if(noteEl) noteEl.innerHTML = `<div class="cc-note">${escapeHtml(t("cc_sqn_created").replace("{squadron}", created.designation))}</div>`;
          const dEl = $("#cc-sqn-new-desig"); if(dEl) dEl.value = "";
          const cEl = $("#cc-sqn-new-callsign"); if(cEl) cEl.value = "";
          const fEl = $("#cc-sqn-new-fullname"); if(fEl) fEl.value = "";
          commandSquadronsNewRole = null;
          await loadCommandSquadrons();
        } catch(err){
          if(noteEl) noteEl.innerHTML = `<div class="cc-note deny">${escapeHtml(err.message || t("error_generic"))}</div>`;
        }
      })();
      return;
    }
    if(act === "crest-cancel-arm"){
      if(commandSquadronsArmed && commandSquadronsArmed.enCours) return; // addendum 1 : la note est occupée
      commandSquadronsArmed = null;
      renderCommandSquadrons();
      return;
    }
    if(act === "crest-apply"){
      const a = commandSquadronsArmed;
      if(!a || a.gesture !== "crest" || !a.fileBlob) return;
      if(a.enCours) return;
      const squadronId = a.id;
      const fileBlob = a.fileBlob;
      a.erreur = null;
      a.enCours = true;
      ccConfirmOccupe(b);
      (async ()=>{
        try {
          const fd = new FormData();
          fd.append("file", fileBlob);
          const updated = await apiFetch(`/api/command/squadrons/${squadronId}/crest`, {
            method: "PUT", body: fd,
          });
          // Ne recharge pas la liste entière (§8.3, dernier point) : met à
          // jour l'entrée depuis la réponse et re-rend.
          const list = COMMAND_SQUADRONS || [];
          const idx = list.findIndex(s=>s.id===squadronId);
          if(idx >= 0){
            list[idx] = Object.assign({}, list[idx], {
              crest_sha: updated.crest_sha,
              aircraft: updated.aircraft !== undefined ? updated.aircraft : list[idx].aircraft,
              designation: updated.designation,
              callsign: updated.callsign,
              full_name: updated.full_name,
              status: updated.status,
              discord_role_id: updated.discord_role_id,
            });
          }
          a.enCours = false;
          commandSquadronsArmed = null;
          renderCommandSquadrons();
          // Lot « Le Centre de Commandement dit ce qu'il fait » (R11.1) : l'écusson posé se confirme.
          const noteCrest = $("#cc-sqn-create-note");
          if(noteCrest) noteCrest.innerHTML = `<div class="cc-note">${escapeHtml(t("cc_sqn_crest_done").replace("{squadron}", updated.designation))}</div>`;
        } catch(err){
          a.enCours = false;
          a.erreur = err.message || t("error_generic");
          if(commandSquadronsArmed === a) renderCommandSquadrons();
        }
      })();
      return;
    }
  });

  view.addEventListener("change", e=>{
    const filePick = e.target.closest('input[type="file"][data-act="crest-pick"]');
    if(filePick){
      handleCommandSquadronCrestPick(filePick);
      return;
    }
    const sel = e.target.closest("select.cc-set");
    if(!sel) return;
    const act = sel.dataset.act;
    const value = sel.value || null;

    if(act === "ed-role"){
      commandSquadronsEditRole = value;
      renderCommandSquadronsNote();
      return;
    }
    if(act === "sqn-wake-role"){
      if(commandSquadronsArmed && commandSquadronsArmed.enCours) return; // addendum 1 : la note est occupée
      if(commandSquadronsArmed){
        commandSquadronsArmed.roleChoisi = value;
        commandSquadronsArmed.refus = false;
        commandSquadronsArmed.erreur = null; // addendum 1 (A2) : le refus suit le choix
      }
      renderCommandSquadronsNote();
      return;
    }
    if(act === "new-role"){
      commandSquadronsNewRole = value;
      return;
    }
  });

  view.addEventListener("input", e=>{
    const el = e.target.closest("[data-act]");
    if(!el) return;
    if(el.dataset.act === "ed-desig"){ commandSquadronsEditDesig = el.value; renderCommandSquadronsNote(); }
    if(el.dataset.act === "ed-callsign"){ commandSquadronsEditCallsign = el.value; }
    if(el.dataset.act === "ed-full"){ commandSquadronsEditFull = el.value; }
    if(el.dataset.act === "ed-nickname"){ commandSquadronsEditNickname = el.value; }
    // Lot « La config d'escadre… » : le nom d'une livrée custom se saisit sans refaire l'écran (le focus reste) ; les
    // listes de la livrée par défaut, elles, suivent. Le choix d'une livrée du jeu ne refait que ces listes ; changer
    // l'appareil d'une livrée du jeu vide son nom et refait l'écran.
    if(el.dataset.act === "liv-nom" || el.dataset.act === "liv-jeu-nom" || el.dataset.act === "liv-def" || el.dataset.act === "liv-jeu-ac"){
      const l = commandSquadronsEditLiveries[Number(el.dataset.i)];
      if(el.dataset.act === "liv-def"){
        if(el.value) commandSquadronsEditDefaults[el.dataset.code] = el.value; else delete commandSquadronsEditDefaults[el.dataset.code];
      } else if(l){
        const ancien = String(l.name || "").trim();
        if(el.dataset.act === "liv-jeu-ac"){
          // Changer l'appareil d'une livrée du jeu vide son nom et retire la livrée par défaut qui la nommait.
          const avant = l.aircraft.slice();
          l.aircraft = el.value ? [el.value] : []; l.name = "";
          avant.forEach(c => commandSquadronLivSuivre(c, ancien, null));
          commandSquadronsLivErr = null;
          renderCommandSquadrons();
          return;
        }
        if(el.dataset.act === "liv-nom"){
          // Un renommage de custom se saisit sans refaire l'écran ; la livrée par défaut le suit à la validation (`change`).
          if(l.nomRef === undefined) l.nomRef = ancien;
          l.name = el.value;
        } else {
          l.name = el.value;
          l.aircraft.forEach(c => commandSquadronLivSuivre(c, ancien, null));
        }
        commandSquadronsLivErr = null;
        const zone = view.querySelector('[data-zone="liv-defauts"]');
        if(zone) zone.innerHTML = commandSquadronLivDefautsHtml();
      }
    }
    if(el.dataset.act === "ac-add"){
      if(el.value === "__autre__"){
        commandSquadronsEditAircraftOther = "";
        renderCommandSquadrons();
        const champ = view.querySelector('[data-act="ac-other"]');
        if(champ) champ.focus();
      } else if(el.value){
        commandSquadronsAddAircraft(el.value);
      }
    }
    if(el.dataset.act === "ac-other"){ commandSquadronsEditAircraftOther = el.value; }
  });

  // Lot « La config d'escadre… » : le nom d'une livrée custom est validé (`change`) : la livrée par défaut qui le portait le suit.
  view.addEventListener("change", e=>{
    const el = e.target.closest('[data-act="liv-nom"]');
    if(!el) return;
    const l = commandSquadronsEditLiveries[Number(el.dataset.i)];
    if(!l || l.nomRef === undefined) return;
    const ancien = l.nomRef, nouveau = String(l.name || "").trim();
    delete l.nomRef;
    if(ancien === nouveau) return;
    l.aircraft.forEach(c => commandSquadronLivSuivre(c, ancien, nouveau));
    const zone = view.querySelector('[data-zone="liv-defauts"]');
    if(zone) zone.innerHTML = commandSquadronLivDefautsHtml();
  });

  // Lot « L'appareil de l'escadrille » -- Entrée dans le champ « Autre » vaut « Ajouter ».
  view.addEventListener("keydown", e=>{
    if(e.key !== "Enter" || !e.target.matches('[data-act="ac-other"]')) return;
    e.preventDefault();
    commandSquadronsAddAircraft(e.target.value);
  });
}

/* ===================================================================
   Lot 3.2c « Les membres » — Centre de Commandement, écran Membres.
   Deuxième domaine servi. Regroupement par escadrille recopié de
   l'écran hebdo (app.js:1510-1522, cf. brief §6.2) : "Free Agent"
   toujours en dernier, quel que soit l'alphabet -- valeur de donnée
   (app/squadron.py, FREE_AGENT), jamais traduite.
   =================================================================== */
let commandMembersLoadState = "idle"; // idle | loading | ready | error
let commandMembersError = null;
let COMMAND_MEMBERS = null;
// Lot « L'appel » : le compte rendu du dernier appel, porté par
// GET /command/members, et le bouton « Faire l'appel ».
let COMMAND_APPEL = null;
let commandAppelRunning = false;

function appelNoms(list){
  const n = list.map(callsign);
  return n.length < 2 ? n.join("") : n.slice(0, -1).join(", ") + " " + t("cc_appel_and") + " " + n[n.length - 1];
}

function appelPhrase(cle, list, sq){
  return t(cle + (list.length === 1 ? "_one" : "_n")).replace("{names}", appelNoms(list)).replace("{sq}", sq || "");
}

// Le compte rendu en une ligne : qui sort, qui change de case, qui revient,
// qui arrive -- des verbes conjugués, jamais un participe accordé (texte neutre).
function appelBilan(a){
  if(a.erreur) return t("cc_appel_error").replace("{reason}", a.erreur);
  const l = [];
  if((a.sortent || []).length) l.push(appelPhrase("cc_appel_out", a.sortent));
  (a.bougent || []).forEach(g => l.push(g.vers ? appelPhrase("cc_appel_move", g.noms, g.vers) : appelPhrase("cc_appel_fa", g.noms)));
  if((a.reviennent || []).length) l.push(appelPhrase("cc_appel_back", a.reviennent));
  // Lot « L'effectif complet » (R195) : les arrivées, groupées comme les
  // changements de case ; puis, si la liste du serveur a manqué, pourquoi.
  (a.arrivent || []).forEach(g => l.push(g.vers ? appelPhrase("cc_appel_in", g.noms, g.vers) : appelPhrase("cc_appel_in_fa", g.noms)));
  const bilan = l.length ? l.join(" · ") : t("cc_appel_none");
  return a.liste ? bilan + " · " + t("cc_appel_list_ko").replace("{reason}", a.liste) : bilan;
}

// La ligne d'appel (#cc-mbr-appel), en tête de l'écran Membres : la date du
// dernier appel, le bouton, le compte rendu. Vide tant que la liste n'est pas
// prête ; en refus (.deny) si l'appel s'est interrompu.
function renderCommandAppel(){
  const zone = $("#cc-mbr-appel");
  if(!zone) return;
  if(commandMembersLoadState !== "ready"){ zone.innerHTML = ""; return; }
  const a = COMMAND_APPEL;
  const quand = a ? `${escapeHtml(t("cc_appel_last"))} · ${escapeHtml(fmtLocalDate(a.at))} · ${escapeHtml(fmtParisTime(a.at))}` : "";
  const bouton = `<button type="button" class="btn btn-sm cc-act" id="cc-appel-btn"${commandAppelRunning ? " disabled" : ""}>${escapeHtml(t(commandAppelRunning ? "cc_appel_running" : "cc_appel_btn"))}</button>`;
  const bilan = a ? `<span class="cc-appel-bilan">${escapeHtml(appelBilan(a))}</span>` : "";
  zone.innerHTML = `<div class="cc-note cc-appel${a && a.erreur ? " deny" : ""}"><span class="cc-appel-quand">${quand}</span>${bouton}${bilan}</div>`;
}

// Lot « Les relances » (R8) : la liste des pilotes en retard de planning
// (#cc-mbr-relances), sous la ligne d'appel -- une .cc-note.cc-appel, la même
// famille, sans règle neuve. Lue sur GET /command/relances à l'entrée de
// l'écran, puis après chaque appel au bouton. Les noms arrivent du serveur
// sans préfixe d'escadrille : jamais repassés par callsign(). Absente tant
// que la route n'a pas répondu, et si elle échoue.
let COMMAND_RELANCES = null;
// Lot « Le Centre au doigt et à la charte » (R3) : la liste des retards est repliée tant qu'on ne l'a pas ouverte ;
// jamais remis à `false`, jamais stocké.
let commandRelancesOuvert = false;

// « 2026-08-14 » (date de Paris) ou un instant ISO 8601 -> « 14/08 ».
function relancesJourMois(iso){
  if(/^\d{4}-\d{2}-\d{2}$/.test(iso)) return iso.slice(8, 10) + "/" + iso.slice(5, 7);
  return new Date(iso).toLocaleDateString("fr-FR", {day:"2-digit", month:"2-digit", timeZone:fuseauEscadre()});
}

function renderCommandRelances(){
  const zone = $("#cc-mbr-relances");
  if(!zone) return;
  const r = COMMAND_RELANCES;
  if(!r){ zone.innerHTML = ""; return; }
  const ligne = html => `<span class="cc-appel-bilan">${html}</span>`;
  const retards = r.retards || [];
  // Un pilote par ligne : sur téléphone, plusieurs pilotes sur une ligne se
  // coupent au milieu d'un nom.
  const pilote = p => ligne(escapeHtml(p.nom) + " — " + escapeHtml(p.derniere_reponse
    ? t("cc_relances_last").replace("{date}", relancesJourMois(p.derniere_reponse))
    : t("cc_relances_never")));
  const blocs = retards.length
    ? retards.map(g => `<span class="cc-appel-quand">${escapeHtml(g.escadrille)}</span>` + g.pilotes.map(pilote).join("")).join("")
    : ligne(escapeHtml(t("cc_relances_none")));
  const dest = r.destinataires || [];
  const destLigne = ligne(escapeHtml(dest.length
    ? t("cc_relances_dest").replace("{names}", dest.map(d => d.nom).join(", "))
    : t("cc_relances_dest_none")));
  const refus = (r.refus || []).map(x => ligne(escapeHtml(
    t("cc_relances_refus").replace("{name}", x.destinataire.nom).replace("{date}", relancesJourMois(x.le)))));
  // Lot « Le Centre au doigt et à la charte » (R3) : avec des pilotes en retard, la liste est repliée derrière son
  // titre, qui dit leur nombre ; sans retard, la note d'aujourd'hui.
  const n = retards.reduce((somme, g) => somme + (g.pilotes || []).length, 0);
  if(n > 0){
    const o = commandRelancesOuvert;
    const compte = t("cc_relances_n").split("{n}").join(String(n)).split("{s}").join(n > 1 ? "s" : "");
    zone.innerHTML = `<div class="cc-note cc-appel"><span class="cc-appel-bilan"><button type="button" class="cc-relances-titre" data-act="relances-plier" aria-controls="cc-relances-liste" aria-expanded="${o}"><span class="chev" aria-hidden="true">${o ? "▾" : "▸"}</span><b>${escapeHtml(t("cc_relances_title"))}</b><span class="cc-relances-n">${escapeHtml(compte)}</span></button></span><div class="cc-relances-liste" id="cc-relances-liste"${o ? "" : " hidden"}>${blocs}</div>${destLigne}${refus.join("")}</div>`;
    return;
  }
  // Le titre a sa propre ligne (.cc-appel-bilan prend toute la largeur) : sans
  // elle, il se lirait collé au nom de la première escadrille.
  zone.innerHTML = `<div class="cc-note cc-appel"><span class="cc-appel-bilan"><b>${escapeHtml(t("cc_relances_title"))}</b></span>${blocs}${destLigne}${refus.join("")}</div>`;
}

async function loadCommandRelances(){
  try {
    COMMAND_RELANCES = await apiFetch("/api/command/relances");
  } catch(e){
    COMMAND_RELANCES = null;
  }
  renderCommandRelances();
}

// POST /command/members/appel rend la charge de GET /command/members, lue
// après l'appel : un seul aller-retour, aucun rechargement visible.
async function lancerAppel(){
  if(estInviteEcran()){ showToast(t("invite_lecture_seule")); return; } // lot « L'accès invité » (R11) : ni « en cours », ni note d'échec
  if(commandAppelRunning) return;
  commandAppelRunning = true;
  renderCommandAppel();
  try {
    const data = await apiFetch("/api/command/members/appel", {method:"POST"});
    COMMAND_MEMBERS = data.members || [];
    COMMAND_APPEL = data.appel || null;
  } catch(e){
    COMMAND_APPEL = {at: new Date().toISOString(), erreur: e.message || t("error_generic")};
  }
  await loadCommandRelances(); // lot « Les relances » : la passe a pu envoyer des MP
  commandAppelRunning = false;
  renderCommandMembers();
}

async function loadCommandMembers(){
  commandMembersLoadState = "loading";
  commandMembersError = null;
  renderCommandMembers();
  try {
    const data = await apiFetch("/api/command/members");
    COMMAND_MEMBERS = data.members || [];
    COMMAND_APPEL = data.appel || null;
    commandMembersLoadState = "ready";
  } catch(e){
    commandMembersLoadState = "error";
    commandMembersError = e.message || t("error_generic");
  }
  renderCommandMembers();
}

function ensureCommandMembersLoaded(){
  if(commandMembersLoadState === "ready" || commandMembersLoadState === "loading"){
    renderCommandMembers();
    return;
  }
  loadCommandMembers();
}

// Brief §6.6 : quatre lignes de squelette, quatre cellules -- largeurs
// variées par colonne (defaut relevé au 3.2b, checkpoint v0.99 §6, à ne
// pas reproduire ici : ne pas mettre quatre largeurs identiques).
// `.skel-row` retiré (dette 15, dernier foyer, Lot 3.3 §6) : la classe
// n'a jamais porté aucune règle d'apparence, cf. cssrules.py -- son
// retrait ici coûte zéro règle, même geste que commandSquadronsSkeletonRowsHtml.
function commandMembersSkeletonRowsHtml(){
  const widths = ["60%", "40%", "25%", "55%"];
  const row = `<tr>${widths.map(w=>`<td><span class="skel" style="width:${w}"></span></td>`).join("")}</tr>`;
  return row.repeat(4);
}

// Brief §6.2 : tri et regroupement recopiés à l'identique de l'écran
// hebdo (app.js:1510-1522) -- ne pas réinventer.
function commandMembersGrouped(list){
  const groupsMap = new Map();
  list.forEach(m=>{
    const sq = m.squadron || "Free Agent";
    if(!groupsMap.has(sq)) groupsMap.set(sq, []);
    groupsMap.get(sq).push(m);
  });
  const groupKeys = Array.from(groupsMap.keys()).sort((a,b)=>{
    if(a==="Free Agent" && b==="Free Agent") return 0;
    if(a==="Free Agent") return 1;
    if(b==="Free Agent") return -1;
    return a.localeCompare(b);
  });
  groupKeys.forEach(sq=> groupsMap.get(sq).sort((a,b)=> a.name.localeCompare(b.name)));
  return {groupKeys, groupsMap};
}

// Brief §6.1 : rang "member" partout aujourd'hui -- c'est le point (3.2d
// comble le manque). §6.4 : repère du lecteur, bordure d'accent, jamais
// de fond.
function commandMemberRowHtml(m){
  const rankKey = m.rank === "leader" ? "cc_mbr_rank_leader"
    : m.rank === "deputy" ? "cc_mbr_rank_deputy"
    : m.rank === "member" ? "cc_mbr_rank_member"
    : null;
  const rankLabel = rankKey ? escapeHtml(t(rankKey)) : "—";
  const isYou = ME && String(m.id) === String(ME.id);
  const seen = m.last_login_at ? escapeHtml(fmtLocalDate(m.last_login_at)) : "—";
  return `<tr${isYou ? ' class="cc-you"' : ""}>
    <td><span class="mbr-name"><span class="avatar">${avatarHtml(m.id, m.avatar_hash, m.name)}</span>${escapeHtml(callsign(m.name))}</span></td>
    <td class="mbr-rank">${rankLabel}</td>
    <td>${m.is_admin ? `<span class="mbr-admin" data-i18n="cc_mbr_admin_yes">${escapeHtml(t("cc_mbr_admin_yes"))}</span>` : ""}</td>
    <td class="mbr-seen">${seen}</td>
  </tr>`;
}

// Lot « Le Centre au doigt et à la charte » (R2) : la recherche d'un membre filtre le tableau à la frappe. Une bande de
// groupe est cachée quand aucun membre de son groupe ne reste ; le compte se dit sous la saisie.
function ccFiltrerMembres(){
  const champ = $("#cc-mbr-q");
  const tbody = $("#cc-mbr-tbody");
  if(!champ || !tbody) return;
  const v = champ.value.trim().toLowerCase();
  let n = 0;
  let bande = null, bandeVisible = false;
  const fermerBande = ()=>{ if(bande) bande.classList.toggle("hidden", !bandeVisible); };
  Array.from(tbody.querySelectorAll("tr")).forEach(tr=>{
    if(tr.classList.contains("cc-group")){
      fermerBande();
      bande = tr; bandeVisible = false;
      return;
    }
    const visible = !v || tr.textContent.toLowerCase().includes(v);
    tr.classList.toggle("hidden", !visible);
    if(visible){ n++; bandeVisible = true; }
  });
  fermerBande();
  const compte = $("#cc-mbr-count");
  if(compte) compte.textContent = v ? t("cc_mbr_count").split("{n}").join(String(n)).split("{s}").join(n > 1 ? "s" : "") : "";
}

function commandMembersGroupRowHtml(sq){
  return `<tr class="cc-group"><td colspan="4"><span class="cc-group-label">${escapeHtml(sq)}</span></td></tr>`;
}

function renderCommandMembers(){
  const table = $("#cc-mbr-table");
  const tbody = $("#cc-mbr-tbody");
  const wrap = table ? table.closest(".cc-wrap") : null;
  const emptyEl = $("#cc-mbr-empty");
  const errorEl = $("#cc-mbr-error");
  if(!table || !tbody || !wrap || !emptyEl || !errorEl) return;
  renderCommandAppel();
  renderCommandRelances();
  renderCommandAcces();

  // Lot « Le Centre au doigt et à la charte » (R2) : la ligne de recherche suit le tableau.
  const rechercheEl = $("#cc-mbr-search");
  const suivreTableau = ()=>{ if(rechercheEl) rechercheEl.classList.toggle("hidden", wrap.classList.contains("hidden")); };
  wrap.classList.add("hidden");
  emptyEl.classList.add("hidden");
  errorEl.classList.add("hidden");
  suivreTableau();

  if(commandMembersLoadState === "loading"){
    wrap.classList.remove("hidden");
    suivreTableau();
    tbody.innerHTML = commandMembersSkeletonRowsHtml();
    ccStampLabels();
    return;
  }
  if(commandMembersLoadState === "error"){
    errorEl.classList.remove("hidden");
    return;
  }
  const list = COMMAND_MEMBERS || [];
  if(list.length === 0){
    emptyEl.classList.remove("hidden");
    return;
  }
  wrap.classList.remove("hidden");
  suivreTableau();
  const {groupKeys, groupsMap} = commandMembersGrouped(list);
  tbody.innerHTML = groupKeys.map(sq =>
    commandMembersGroupRowHtml(sq) + groupsMap.get(sq).map(commandMemberRowHtml).join("")
  ).join("");
  ccStampLabels();
  ccFiltrerMembres();
}

/* Lot « Polish du Centre » : le diagnostic d'accès, à l'écran Membres, pour un administrateur seul.
   Un membre choisi : ses rôles Discord relevés et, droit par droit, s'il l'a et ce qui le lui ouvre.
   Le serveur rend le verdict des vrais résolveurs (GET /command/members/{id}/acces) ; l'écran ne
   calcule rien. Les rôles se nomment par l'annuaire des rôles du serveur (ccRoleName). */
let commandAccesPid = null;      // le membre choisi, ou null
let commandAccesState = "idle";  // idle | loading | ready | error
let COMMAND_ACCES = null;        // {roles:[…], droits:[{cle, accorde, source}]}
// Lot « La connexion de secours » (R325) : le lien de secours du membre choisi. Jamais conservé : ni stockage,
// ni rechargement ; choisir un autre membre l'efface.
let commandLien = null;          // null | {etat:"loading"} | {etat:"ready", url, until} | {etat:"refus"} | {etat:"error"}

function commandAccesSourceText(s){
  if(!s) return t("cc_diag_s_aucun");
  if(s.type === "role") return escFill(t("cc_diag_s_role"), {role: ccRoleName(s.role_id)});
  if(s.type === "adjoint") return escFill(t("cc_diag_s_adjoint"), {escadrille: s.escadrille});
  return t("cc_diag_s_" + s.type);   // admin · compte
}

// Lot « La connexion de secours » : le bloc du lien de secours, sous le tableau des droits (mobilier existant).
function commandLienHtml(){
  const l = commandLien;
  let suite = "";
  if(l && l.etat === "ready"){
    suite = `<div class="cc-row"><input class="cc-set" type="text" readonly size="48" data-act="lien-url" value="${escapeAttr(l.url)}" aria-label="${escapeAttr(t("cc_lien_title"))}"><button type="button" class="btn btn-sm cc-act" data-act="lien-copy">${escapeHtml(t("cc_lien_copy"))}</button></div>
      <p class="cc-hint">${escFill(escapeHtml(t("cc_lien_until")), {date: escapeHtml(l.date), heure: escapeHtml(l.heure)})}</p>`;
  } else if(l && l.etat === "refus"){
    suite = `<div class="cc-note deny">${escapeHtml(t("cc_lien_refus"))}</div>`;
  } else if(l && l.etat === "error"){
    suite = `<div class="cc-note deny">${escapeHtml(t("cc_lien_error"))}</div>`;
  }
  return `<div class="cc-block"><h3 class="cc-sub">${escapeHtml(t("cc_lien_title"))}</h3>
    <p class="cc-hint">${escapeHtml(t("cc_lien_hint"))}</p>
    <div class="cc-row"><button type="button" class="btn btn-sm cc-act" data-act="lien-emettre"${l && l.etat === "loading" ? " disabled" : ""}>${escapeHtml(t("cc_lien_btn"))}</button></div>
    ${suite}</div>`;
}

function commandAccesHtml(){
  const membres = (COMMAND_MEMBERS || []).slice().sort((a,b)=> callsign(a.name).localeCompare(callsign(b.name)));
  const options = `<option value="">${escapeHtml(t("cc_diag_choose"))}</option>` + membres.map(m =>
    `<option value="${escapeAttr(String(m.id))}"${String(m.id) === String(commandAccesPid) ? " selected" : ""}>${escapeHtml(callsign(m.name))} · ${escapeHtml(m.squadron || "Free Agent")}</option>`
  ).join("");
  let corps = "";
  if(commandAccesPid && commandAccesState === "loading"){
    corps = `<div class="cc-fiche"><span class="skel" style="width:70%"></span><span class="skel" style="width:55%"></span></div>`;
  } else if(commandAccesPid && commandAccesState === "error"){
    corps = `<div class="cc-note deny">${escapeHtml(t("cc_diag_error"))}</div>`;
  } else if(commandAccesPid && COMMAND_ACCES){
    const d = COMMAND_ACCES;
    const roles = d.roles.length ? d.roles.map(r => escapeHtml(ccRoleName(r))).join(" · ") : escapeHtml(t("cc_diag_roles_none"));
    corps = `<div class="cc-note">${escFill(escapeHtml(t("cc_diag_roles")), {roles})}</div>
      <div class="cc-wrap"><table class="cc-table"><thead><tr>
        <th>${escapeHtml(t("cc_diag_col_droit"))}</th><th>${escapeHtml(t("cc_diag_col_accorde"))}</th><th>${escapeHtml(t("cc_diag_col_par"))}</th>
      </tr></thead><tbody>${d.droits.map(x => `<tr>
        <td>${escapeHtml(t("cc_diag_d_" + x.cle.replace(/\./g, "_")))}</td>
        <td><span class="cc-office${x.accorde ? " porte" : ""}">${escapeHtml(t(x.accorde ? "cc_diag_oui" : "cc_diag_non"))}</span></td>
        <td class="sqn-full">${escapeHtml(commandAccesSourceText(x.source))}</td>
      </tr>`).join("")}</tbody></table></div>${commandLienHtml()}`;
  }
  return `<div class="cc-block"><h3 class="cc-sub">${escapeHtml(t("cc_diag_title"))}</h3>
    <p class="cc-hint">${escapeHtml(t("cc_diag_hint"))}</p>
    <div class="cc-row"><select class="cc-set" data-act="acces-pick" aria-label="${escapeAttr(t("cc_diag_title"))}">${options}</select></div>
    ${corps}</div>`;
}

function renderCommandAcces(){
  const box = $("#cc-mbr-acces");
  if(!box) return;
  if(!(ME && ME.is_admin === true) || commandMembersLoadState !== "ready"){ box.innerHTML = ""; return; }
  box.innerHTML = commandAccesHtml();
  ccStampLabels(box);
}

async function loadCommandAcces(pid){
  commandAccesPid = pid || null;
  COMMAND_ACCES = null;
  commandLien = null;   // choisir un autre membre efface le lien affiché
  if(!commandAccesPid){ commandAccesState = "idle"; renderCommandAcces(); return; }
  commandAccesState = "loading";
  renderCommandAcces();
  let d = null, ok = true;
  try {
    await ensureCommandDiscordRolesLoaded();
    d = await apiFetch(`/api/command/members/${encodeURIComponent(commandAccesPid)}/acces`);
  } catch(e){ ok = false; }
  if(String(pid) !== String(commandAccesPid)) return;   // un autre membre choisi entre-temps
  COMMAND_ACCES = d;
  commandAccesState = ok ? "ready" : "error";
  renderCommandAcces();
}

document.addEventListener("change", e=>{
  const sel = e.target.closest && e.target.closest('[data-act="acces-pick"]');
  if(sel) loadCommandAcces(sel.value);
});

// Lot « La connexion de secours » : émettre le lien de secours du membre choisi (POST, administrateur seul).
async function emettreLienSecours(){
  const pid = commandAccesPid;
  if(!pid || (commandLien && commandLien.etat === "loading")) return;
  commandLien = {etat:"loading"};
  renderCommandAcces();
  let res;
  try {
    const d = await apiFetch(`/api/command/members/${encodeURIComponent(pid)}/lien-secours`, {method:"POST"});
    res = {etat:"ready", url:d.url, date:fmtLocalDate(d.expires_at), heure:fmtLocalTime(d.expires_at)};
  } catch(e){
    res = {etat: e && e.status === 409 ? "refus" : "error"};
  }
  if(String(pid) !== String(commandAccesPid)) return;   // un autre membre choisi entre-temps
  commandLien = res;
  renderCommandAcces();
}

// Copie du lien : presse-papiers, repli par sélection du champ et `execCommand("copy")`.
async function copierLienSecours(){
  const url = commandLien && commandLien.url;
  const champ = document.querySelector('#cc-mbr-acces input[data-act="lien-url"]');
  if(!url || !champ) return;
  let copie = false;
  try {
    await navigator.clipboard.writeText(url);
    copie = true;
  } catch(e){
    try {
      champ.focus();
      champ.select();
      champ.setSelectionRange(0, url.length);
      copie = document.execCommand("copy");
    } catch(e2){ /* le champ reste sélectionné : copie à la main */ }
  }
  if(copie) showToast(t("cc_lien_copied"));
}

document.addEventListener("click", e=>{
  const b = e.target.closest && e.target.closest('#cc-mbr-acces [data-act="lien-emettre"], #cc-mbr-acces [data-act="lien-copy"]');
  if(!b) return;
  if(b.dataset.act === "lien-emettre") emettreLienSecours();
  else copierLienSecours();
});

/* ===================================================================
   Lot 3.2d « Les Droits », premier temps — Centre de Commandement,
   écran Droits. Troisième domaine servi. `GET /command/rights` et
   `GET /command/discord-roles` chargés ensemble (Promise.all) -- le
   second alimente les noms de rôle affichés (jamais d'identifiant nu,
   sauf rôle référencé absent du serveur, brief §8.3/P23). L'annuaire
   des membres (`GET /command/members`) n'est PAS dans ce Promise.all
   (correctif C3, 0.9903) : il ne sert que le bloc des éditeurs
   nominatifs, réservé à l'admin -- un chef d'escadrille n'a aucune
   raison d'être exposé à son échec. Demandé séparément, uniquement si
   `rights.you.is_admin`, échec absorbé (COMMAND_RIGHTS_DIRECTORY reste
   `null`, l'écran passe quand même en `ready`). Quatre états :
   chargement (squelettes largeurs variées), vide (aucune escadrille
   active), erreur (échec GET /rights, bouton de réessai), partiel
   (bandeau au-dessus du contenu, au moins une escadrille active sans
   chef). Désigner/retirer un chef et retenir/vider le rôle Discord des
   chefs s'annoncent dans .cc-note avant d'être appliqués (Confirmer/
   Annuler, aucun appel réseau avant confirmation, brief §8.2) ;
   l'adjoint et les éditeurs du planning s'appliquent immédiatement
   (mobilier .cc-note réemployé pour l'ANNONCE du résultat, pas pour
   une confirmation préalable -- absents de la liste du §8.2).
   =================================================================== */
let commandRightsLoadState = "idle"; // idle | loading | ready | error
let commandRightsError = null;
let COMMAND_RIGHTS = null;
let COMMAND_DISCORD_ROLES = null; // {roles:[{id,name}], available}
let COMMAND_RIGHTS_DIRECTORY = null; // annuaire complet (GET /command/members), admin seul -- résout les profils hors escadrille active (Free Agents), P23 ; reste null si non-admin ou si la requête échoue (correctif C3)
let commandRightsAddMode = null;  // null | "role" | "id" | "conn" | "sess" | "evt"
let commandRightsPending = null;  // callback de l'action en attente de confirmation (blocs 1/2)
let commandRightsConnArmed = null;  // id du rôle d'accès armé pour retrait, ou null (bloc 4, local)
let commandRightsConnEnCours = false; // Addendum 1 (A1) : vrai du clic sur « Appliquer » de la note de retrait à l'issue de l'appel
let commandRightsEnCours = false;     // Addendum 1 (A1) : idem pour la note de confirmation de `showCommandRightsNote` (`cc-confirm`)
let commandRightsConnErreur = null; // Lot « Le Centre au doigt et à la charte » (R5) : le refus du serveur, dans la note ; remis à null à chaque armement, annulation ou succès
let commandRightsNoteCourante = null; // {titre, text, deny} de la note de confirmation ouverte, pour la redessiner avec un refus

async function loadCommandRights(){
  invitesLoadState = "idle"; // lot « L'accès invité » : la liste des invités se relit
  commandRightsLoadState = "loading";
  commandRightsError = null;
  commandRightsAddMode = null;
  commandRightsConnArmed = null;
  COMMAND_RIGHTS_DIRECTORY = null;
  renderCommandRights();
  try {
    const [rights] = await Promise.all([
      apiFetch("/api/command/rights"),
      ensureCommandDiscordRolesLoaded(),
    ]);
    COMMAND_RIGHTS = rights;
    commandRightsLoadState = "ready";
    // Annuaire : demandé séparément, admin seul, échec absorbé (C3) --
    // ne doit jamais faire basculer l'écran en erreur pour un chef.
    if(rights.you && rights.you.is_admin){
      try {
        const members = await apiFetch("/api/command/members");
        COMMAND_RIGHTS_DIRECTORY = members.members || [];
      } catch(e){
        COMMAND_RIGHTS_DIRECTORY = null; // repli : identifiant + mention d'absence, comme un rôle absent du serveur
      }
    }
  } catch(e){
    commandRightsLoadState = "error";
    commandRightsError = e.message || t("error_generic");
  }
  renderCommandRights();
}

function ensureCommandRightsLoaded(){
  if(commandRightsLoadState === "ready" || commandRightsLoadState === "loading"){
    renderCommandRights();
    return;
  }
  loadCommandRights();
}

// Squelette de chargement -- largeurs variées (jamais uniformes, défaut
// du 3.2b, cf. checkpoint v0.99 §6). Mobilier réemployé uniquement
// (.cc-block, .cc-wrap, .cc-table, .cc-row, .skel) -- aucune règle CSS
// neuve. `.skel-row` retiré (dette 15, dernier foyer, Lot 3.3 §6) : la
// classe n'a jamais porté aucune règle d'apparence. Étendu au Lot 3.3
// (§6) pour couvrir les DEUX blocs neufs -- bloc 5 (une rangée de
// pastilles) et bloc 6 (le tableau de référence, quatre lignes) --
// largeurs reprises de la bascule « État de chargement » de la
// maquette validée.
function commandRightsSkeletonHtml(){
  const rows = [["55%","40%","30%"], ["65%","35%","45%"], ["50%","60%","25%"], ["70%","30%","55%"]];
  const refRows = [["45%","70%","30%"], ["60%","40%","22%"], ["38%","85%","26%"], ["52%","55%","18%"]];
  return `<div class="cc-block"><span class="skel" style="width:38%;height:1rem;display:inline-block"></span></div>
    <div class="cc-wrap"><table class="cc-table"><tbody>
      ${rows.map(w=>`<tr>${w.map(x=>`<td><span class="skel" style="width:${x}"></span></td>`).join("")}</tr>`).join("")}
    </tbody></table></div>
    <div class="cc-block"><span class="skel" style="width:32%;height:1rem;display:inline-block"></span>
      <div class="cc-row">${["120px","96px","140px"].map(w=>`<span class="skel" style="width:${w};height:1.5rem"></span>`).join("")}</div>
    </div>
    <div class="cc-wrap"><table class="cc-table"><tbody>
      ${refRows.map(w=>`<tr>${w.map(x=>`<td><span class="skel" style="width:${x}"></span></td>`).join("")}</tr>`).join("")}
    </tbody></table></div>`;
}

// Nom d'un rôle Discord depuis son id -- jamais d'identifiant nu, sauf
// rôle référencé en base mais absent du serveur (P23).
function ccRoleName(roleId){
  if(roleId == null) return "";
  const found = COMMAND_DISCORD_ROLES && (COMMAND_DISCORD_ROLES.roles||[]).find(r=>String(r.id)===String(roleId));
  return found ? found.name : (roleId + " · " + t("cc_rights_role_absent"));
}

function ccRoleSelectHtml(currentId, act){
  const opts = (COMMAND_DISCORD_ROLES && COMMAND_DISCORD_ROLES.roles) || [];
  const known = currentId != null && opts.some(r=>String(r.id)===String(currentId));
  let html = `<select class="cc-set" data-act="${act}">`;
  html += `<option value=""${currentId==null?" selected":""}>— ${escapeHtml(t("cc_rights_role_none"))} —</option>`;
  html += opts.map(r=>`<option value="${escapeHtml(r.id)}"${String(r.id)===String(currentId)?" selected":""}>${escapeHtml(r.name)}</option>`).join("");
  if(currentId != null && !known){
    html += `<option value="${escapeHtml(currentId)}" selected>${escapeHtml(ccRoleName(currentId))}</option>`;
  }
  return html + `</select>`;
}

// Lot « Le Centre de Commandement dit ce qu'il fait » (R9.1, R9.2) : `enPlace` ({leader,
// sansRole}), quand le chef en place ne figure pas parmi `options` -- il ouvre la liste,
// sélectionné, et porte la mention « sans le rôle des chefs » si le Centre lui est fermé.
function ccPersonSelectHtml(options, currentId, act, squadronId, enPlace){
  let html = `<select class="cc-set" data-act="${act}" data-i="${squadronId}">`;
  if(enPlace){
    const nom = callsign(enPlace.leader.name);
    html += `<option value="${escapeHtml(enPlace.leader.id)}" selected>${escapeHtml(enPlace.sansRole ? t("cc_rights_chef_sans_role_opt").replace("{name}", nom) : nom)}</option>`;
  }
  html += `<option value=""${currentId==null?" selected":""}>— ${escapeHtml(t("cc_rights_role_none"))} —</option>`;
  html += options.map(o=>`<option value="${escapeHtml(o.id)}"${String(o.id)===String(currentId)?" selected":""}>${escapeHtml(callsign(o.name))}</option>`).join("");
  return html + `</select>`;
}

// Pastilles de valeur listée (rôle Discord ou personne), bloc 3. `list`
// : items {id,label} déjà résolus à l'affichage ; `dispo` : candidats
// pas encore listés, pour le contrôle d'ajout.
function ccChipsHtml(list, kind, dispo){
  const chipsHtml = list.map((item,i)=>
    `<span class="cc-chip">${escapeHtml(item.label)}${item.qual?` <span class="qual">${escapeHtml(item.qual)}</span>`:""}<button type="button" data-act="rm-${kind}" data-i="${i}" aria-label="${escapeHtml(t("cc_rights_chip_remove"))}">×</button></span>`
  ).join("");
  if(commandRightsAddMode === kind){
    const already = new Set(list.map(l=>String(l.id)));
    const opts = dispo.filter(o=>!already.has(String(o.id)));
    let sel = `<select class="cc-set" data-act="pick-${kind}">`;
    sel += `<option value="">— ${escapeHtml(t("cc_rights_choose"))} —</option>`;
    sel += opts.map(o=>`<option value="${escapeHtml(o.id)}">${escapeHtml(o.label)}</option>`).join("");
    sel += `</select>`;
    sel += `<button type="button" class="btn btn-sm cc-act" data-act="cancel-add-${kind}">${escapeHtml(t("cc_rights_cancel"))}</button>`;
    return chipsHtml + sel;
  }
  return chipsHtml + `<button type="button" class="btn btn-sm cc-act" data-act="add-${kind}">${escapeHtml(t("cc_rights_add"))}</button>`;
}

// Lot « Le Centre au doigt et à la charte » (R4, R5) : la note de confirmation prend la forme commune ; elle garde ses
// arguments (`commandRightsNoteCourante`) pour se redessiner avec le refus du serveur (`erreur`). `deny` = l'action retire.
function showCommandRightsNote(titre, text, deny, onConfirm, erreur = null){
  commandRightsPending = onConfirm || null;
  commandRightsNoteCourante = onConfirm ? {titre, text, deny} : null;
  const zone = $("#cc-note-zone");
  if(!zone) return;
  zone.innerHTML = onConfirm
    ? ccConfirmHtml({
        titre, texte: text, danger: !!deny, err: erreur, occupe: commandRightsEnCours,
        annuler: "cc-cancel", ok: "cc-confirm", libelle: t("cc_rights_confirm_apply"),
      })
    : `<div class="cc-note${deny?" deny":""}"><span>${text}</span></div>`;
}

function clearCommandRightsNote(){
  commandRightsPending = null;
  commandRightsNoteCourante = null;
  const zone = $("#cc-note-zone");
  if(zone) zone.innerHTML = "";
}

// Lot « Le Centre au doigt et à la charte » (R5) : appelée par la note de confirmation seule, elle LÈVE son échec ;
// c'est la note qui le porte.
async function putSquadronLeader(squadronId, profileId){
  await apiFetch(`/api/command/squadrons/${squadronId}/leader`, {
    method:"PUT", headers:{"Content-Type":"application/json"},
    body: JSON.stringify({profile_id: profileId}),
  });
  await loadCommandRights();
}

async function putSquadronDeputy(squadronId, profileId){
  try {
    await apiFetch(`/api/command/squadrons/${squadronId}/deputy`, {
      method:"PUT", headers:{"Content-Type":"application/json"},
      body: JSON.stringify({profile_id: profileId}),
    });
    await loadCommandRights();
  } catch(e){
    showToast(e.message || t("error_generic"), "erreur");
    renderCommandRights();
  }
}

// Idem : appelée par la note de confirmation seule, elle lève son échec.
async function putChefRole(roleId){
  await apiFetch("/api/command/rights/chef-role", {
    method:"PUT", headers:{"Content-Type":"application/json"},
    body: JSON.stringify({role_id: roleId}),
  });
  await loadCommandRights();
}

async function putEventEditors(nextRoleIds, nextProfileIds){
  try {
    await apiFetch("/api/command/rights/event-editors", {
      method:"PUT", headers:{"Content-Type":"application/json"},
      body: JSON.stringify({role_ids: nextRoleIds, profile_ids: nextProfileIds}),
    });
    await loadCommandRights();
  } catch(e){
    showToast(e.message || t("error_generic"), "erreur");
    renderCommandRights();
  }
}

// Lot « Le Centre au doigt et à la charte » (R5) : appelée depuis la note de retrait (`depuisNote`), elle LÈVE son
// échec -- c'est la note qui le porte ; sinon elle garde son `catch`.
async function putAppAccess(nextRoleIds, depuisNote = false){
  try {
    await apiFetch("/api/command/rights/app-access", {
      method:"PUT", headers:{"Content-Type":"application/json"},
      body: JSON.stringify({role_ids: nextRoleIds}),
    });
    await loadCommandRights();
  } catch(e){
    if(depuisNote) throw e;
    showToast(e.message || t("error_generic"), "erreur");
    renderCommandRights();
  }
}

// Brief « Accès au module Débriefing », 22 août 2026 : même patron exact
// que `putAppAccess` -- route dédiée, liste unique. Aucune 409 sur liste
// vide côté serveur (§5 du brief : vider cette liste ne ferme aucune
// porte).
async function putDebriefAccess(nextRoleIds){
  try {
    await apiFetch("/api/command/rights/debrief-access", {
      method:"PUT", headers:{"Content-Type":"application/json"},
      body: JSON.stringify({role_ids: nextRoleIds}),
    });
    await loadCommandRights();
  } catch(e){
    showToast(e.message || t("error_generic"), "erreur");
    renderCommandRights();
  }
}

// Lot « Les relances » (R7) : route dédiée, listes vides permises (aucun MP ne
// part). Lot « Les relances nominatives » (R3) : les deux listes -- rôles et
// comptes -- partent ENSEMBLE, la route les remplace en entier, comme
// `putEventEditors`. Le serveur lance aussitôt la passe : un destinataire
// ajouté reçoit la liste en cours avant que la réponse revienne.
async function putRelances(nextRoleIds, nextProfileIds){
  try {
    await apiFetch("/api/command/rights/relances", {
      method:"PUT", headers:{"Content-Type":"application/json"},
      body: JSON.stringify({role_ids: nextRoleIds, profile_ids: nextProfileIds}),
    });
    await loadCommandRights();
  } catch(e){
    showToast(e.message || t("error_generic"), "erreur");
    renderCommandRights();
  }
}

// Bloc 5 (Lot 3.3, §3 ; étendu Lot 3.4, §6) : remplacement COMPLET des
// quatre listes en un seul appel, même patron que
// `putEventEditors`/`putAppAccess`. Aucune 409 sur liste vide côté
// serveur -- vider ces listes ne ferme aucune porte.
async function putContentRights(nextSessionRoleIds, nextEventAnyRoleIds, nextCampManageRoleIds, nextCampDeleteRoleIds){
  try {
    await apiFetch("/api/command/rights/content", {
      method:"PUT", headers:{"Content-Type":"application/json"},
      body: JSON.stringify({
        session_edit_role_ids: nextSessionRoleIds,
        event_edit_any_role_ids: nextEventAnyRoleIds,
        campaign_manage_role_ids: nextCampManageRoleIds,
        campaign_delete_role_ids: nextCampDeleteRoleIds,
      }),
    });
    await loadCommandRights();
  } catch(e){
    showToast(e.message || t("error_generic"), "erreur");
    renderCommandRights();
  }
}

// Lot 3.4 §6 : les quatre listes courantes de `COMMAND_RIGHTS`, pour les
// appelants qui n'en modifient qu'une seule -- les trois autres partent
// inchangées dans le même appel (remplacement complet, §6 « même
// transaction, refus global »).
function commandContentRightsLists(){
  const cr = COMMAND_RIGHTS.content_rights || {};
  return {
    sess: (cr.session_edit && cr.session_edit.role_ids) || [],
    evt: (cr.event_edit_any && cr.event_edit_any.role_ids) || [],
    camp: (cr.campaign_manage && cr.campaign_manage.role_ids) || [],
    campdel: (cr.campaign_delete && cr.campaign_delete.role_ids) || [],
  };
}

function renderCommandRights(){
  const loadingEl = $("#cc-droits-loading");
  const emptyEl = $("#cc-droits-empty");
  const errorEl = $("#cc-droits-error");
  const contentEl = $("#cc-droits-content");
  if(!loadingEl || !emptyEl || !errorEl || !contentEl) return;

  loadingEl.innerHTML = "";
  emptyEl.classList.add("hidden");
  errorEl.classList.add("hidden");
  contentEl.classList.add("hidden");

  if(commandRightsLoadState === "loading"){
    loadingEl.innerHTML = commandRightsSkeletonHtml();
    return;
  }
  if(commandRightsLoadState === "error"){
    errorEl.classList.remove("hidden");
    return;
  }
  const data = COMMAND_RIGHTS;
  if(!data) return;

  const squadrons = data.squadrons || [];
  if(squadrons.length === 0){
    emptyEl.classList.remove("hidden");
    return;
  }
  contentEl.classList.remove("hidden");

  const admin = !!data.you.is_admin;
  const mySquadronId = data.you.leads_squadron_id;

  $("#blk-role").classList.toggle("hidden", !admin);
  $("#blk-plan").classList.toggle("hidden", !admin);

  // Lot « Le Centre de Commandement dit ce qu'il fait » (R10) : l'adjoint (ni administrateur,
  // ni chef) lit son rang et le tableau du commandement, en lecture.
  const deputySq = (!admin && mySquadronId == null && data.you.deputy_squadron_id != null)
    ? squadrons.find(s=>s.id === data.you.deputy_squadron_id) : null;

  const partialEl = $("#cc-partial");
  if(!admin && mySquadronId == null && !deputySq){
    partialEl.innerHTML = `<div class="cc-note">${escapeHtml(t("cc_rights_no_squadron"))}</div>`;
    $("#blk-cmd").classList.add("hidden");
  } else {
    $("#blk-cmd").classList.remove("hidden");
    const sansChef = squadrons.filter(s=>!s.leader).map(s=>s.designation);
    // Lot « Le Centre de Commandement dit ce qu'il fait » (R9.3) : les chefs désignés qui ne
    // portent pas le rôle des chefs n'entrent pas au Centre -- l'administrateur le lit en tête.
    const sansRole = squadrons.filter(s=>s.leader && s.leader.centre === false)
      .map(s=>`${s.designation} (${callsign(s.leader.name)})`);
    partialEl.innerHTML = (admin && sansChef.length)
      ? `<div class="cc-note">${escapeHtml(t("cc_rights_partial").replace("{squadrons}", sansChef.join(", ")))}</div>`
      : "";
    if(admin && sansRole.length){
      partialEl.innerHTML += `<div class="cc-note">${escapeHtml(t("cc_rights_partial_sans_role").replace("{squadrons}", sansRole.join(", ")))}</div>`;
    }
  }

  if(admin){
    $("#row-role").innerHTML = ccRoleSelectHtml(data.chef_role_id, "set-rolechef") +
      `<span class="cc-hint">${escapeHtml(t("cc_rights_role_src"))}</span>`;
  }

  $("#hint-cmd").textContent = admin ? t("cc_rights_cmd_hint_admin")
    : deputySq ? t("cc_rights_deputy_note").replace("{squadron}", deputySq.designation)
    : t("cc_rights_cmd_hint_chef");
  $("#tb-cmd").innerHTML = squadrons.map(sq=>{
    const isMine = sq.id === mySquadronId;
    const otherMembers = (sq.members||[]).filter(m=> !sq.leader || String(m.id)!==String(sq.leader.id));

    let chefCell;
    if(admin){
      // Lot « Le Centre de Commandement dit ce qu'il fait » (R9) : le chef en place est toujours
      // nommé, même s'il ne figure pas parmi les candidats (il ne porte plus le rôle des chefs).
      const enPlace = sq.leader && !(sq.candidates||[]).some(c=>String(c.id)===String(sq.leader.id)) ? sq.leader : null;
      const sansRole = !!(sq.leader && sq.leader.centre === false);
      if((sq.candidates||[]).length){
        chefCell = ccPersonSelectHtml(sq.candidates, sq.leader ? sq.leader.id : null, "set-chef", sq.id,
          enPlace ? {leader: enPlace, sansRole} : null);
      } else if(enPlace){
        chefCell = escapeHtml(callsign(enPlace.name)) +
          (sansRole ? `<div class="cc-hint">${escapeHtml(t("cc_rights_chef_sans_role"))}</div>` : "");
      } else {
        chefCell = `<span class="cc-hint">${escapeHtml(data.chef_role_id ? t("cc_rights_no_candidate") : t("cc_rights_pick_role_first"))}</span>`;
      }
    } else {
      chefCell = sq.leader ? escapeHtml(callsign(sq.leader.name)) : "—";
    }

    let deputyCell;
    if(admin || isMine){
      if(otherMembers.length){
        deputyCell = ccPersonSelectHtml(otherMembers, sq.deputy ? sq.deputy.id : null, "set-adj", sq.id);
      } else {
        deputyCell = `<span class="cc-hint">${escapeHtml(t("cc_rights_no_member"))}</span>`;
      }
    } else {
      deputyCell = sq.deputy ? escapeHtml(callsign(sq.deputy.name)) : "—";
    }

    return `<tr${isMine ? ' class="cc-you"' : ""}><td>${escapeHtml(sq.designation)}</td><td>${chefCell}</td><td>${deputyCell}</td></tr>`;
  }).join("");
  ccStampLabels();

  if(admin){
    const ee = data.event_editors || {role_ids:[], profile_ids:[]};
    const roleItems = (ee.role_ids||[]).map(rid=>({id:rid, label: ccRoleName(rid)}));
    const roleDispo = ((COMMAND_DISCORD_ROLES && COMMAND_DISCORD_ROLES.roles) || []).map(r=>({id:r.id, label:r.name}));
    $("#row-plan-roles").innerHTML = ccChipsHtml(roleItems, "role", roleDispo);

    // Annuaire complet (P23) : un profile_id de l'éditeur nominatif peut
    // désigner un Free Agent, absent des escadrilles actives -- jamais
    // résolu depuis GET /rights seul. Repli si l'annuaire est absent
    // (non-admin, ou son chargement a échoué -- correctif C3, 0.9903) ou
    // si le compte n'y figure même pas : identifiant + mention d'absence,
    // exactement le patron déjà prévu pour un rôle absent du serveur
    // (P23 autorise l'identifiant nu dans ce seul cas).
    const directory = COMMAND_RIGHTS_DIRECTORY || [];
    const idItems = (ee.profile_ids||[]).map(pid=>{
      const found = directory.find(m=>String(m.id)===String(pid));
      return {id:pid, label: found ? callsign(found.name) : (pid + " · " + t("cc_rights_role_absent"))};
    });
    const idDispo = directory.map(m=>({id:m.id, label:callsign(m.name)}));
    // Lot « rr-socle-proprete » (v1.0111) : la mention de source (le fichier de configuration) est retirée --
    // la base fait seule autorité pour event.create.
    $("#row-plan-ids").innerHTML = ccChipsHtml(idItems, "id", idDispo);
  }

  // Lot 3.2d Volet 4, second temps (§7) : bloc 4, accès à l'application.
  // Réservé aux administrateurs -- même patron que blk-role/blk-plan
  // (PUT /rights/app-access est admin seul, §6.2 : rien à afficher/éditer
  // ici pour un non-admin).
  $("#blk-conn").classList.toggle("hidden", !admin);
  if(admin){
    renderConnBlock(data);
  }

  // Lot « L'accès invité » (R12) : #blk-invites, entre #blk-conn et #blk-debrief.
  // Réservé aux administrateurs (les cinq routes le sont) -- même patron que
  // blk-conn : absent pour les autres, jamais grisé.
  $("#blk-invites").classList.toggle("hidden", !admin);
  if(admin){
    renderInvitesBlock();
  }

  // Brief « Accès au module Débriefing », 22 août 2026 : sixième bloc,
  // entre blk-conn et blk-droits (§3). Réservé aux administrateurs --
  // même patron que blk-conn (PUT /rights/debrief-access est admin
  // seul) : absent pour les autres, jamais grisé.
  $("#blk-debrief").classList.toggle("hidden", !admin);
  if(admin){
    renderDebriefAccessBlock(data);
  }

  // Lot « Les relances » (R7) : #blk-relances, juste après #blk-debrief.
  // Réservé aux administrateurs -- même patron (PUT /rights/relances est
  // admin seul) : absent pour les autres, jamais grisé.
  $("#blk-relances").classList.toggle("hidden", !admin);
  if(admin){
    renderRelancesBlock(data);
  }

  // Lot 3.3, §3 : bloc 5, droits sur le contenu. Réservé aux
  // administrateurs -- même patron que blk-role/blk-plan/blk-conn
  // (PUT /rights/content est admin seul : rien à afficher/éditer ici
  // pour un non-admin).
  $("#blk-droits").classList.toggle("hidden", !admin);
  if(admin){
    renderContentRightsBlock(data);
  }

  // Lot 3.3, §4 : bloc 6, le tableau de référence. Visible à TOUS (admin
  // ET chef) -- ce n'est pas un outil d'édition, c'est une référence de
  // lecture (§4⑤) ; la maquette validée ne le range pas parmi les blocs
  // réservés à l'administrateur.
  renderRoleReferenceBlock(data);
}

// Lot « L'accès invité » (R12) -- le bloc « Invités — démonstration » de l'écran Droits (administrateur
// seul). Le champ, le bouton « Vérifier » et les zones `#inv-note` et `#inv-liste` sont dans index.html ;
// ici : la liste (GET /command/invites), la vérification d'un compte avant d'inviter, l'invitation, la
// prolongation et la révocation (sans confirmation, puis la liste se recharge).
let INVITES = [];
let invitesLoadState = "idle";   // idle | loading | ready | error
let invitesError = null;
let invitesCompte = null;        // le compte Discord vérifié, prêt à inviter

// Le champ de l'identifiant porte son `aria-label` et son `placeholder` (`cc_inv_id_label`), posés
// ici -- et par `setLang` -- plutôt que par `data-i18n-aria` : l'écran Droits n'en compte pas un de plus.
function renderInvitesChamp(){
  const champ = $("#inv-id");
  if(!champ) return;
  champ.setAttribute("aria-label", t("cc_inv_id_label"));
  champ.setAttribute("placeholder", t("cc_inv_id_label"));
}

function invFmtJusqua(iso){
  return new Date(iso).toLocaleDateString(
    currentLang==="fr" ? "fr-FR" : "en-GB", {day:"numeric", month:"short", year:"numeric"});
}
function invFmtEntree(iso){
  if(!iso) return t("cc_inv_jamais");
  const d = new Date(iso);
  const jour = d.toLocaleDateString(currentLang==="fr" ? "fr-FR" : "en-GB", {day:"numeric", month:"short"});
  const mm = String(d.getMinutes()).padStart(2, "0");
  return currentLang==="fr"
    ? `${jour}, ${d.getHours()} h ${mm}`
    : `${jour}, ${String(d.getHours()).padStart(2, "0")}:${mm}`;
}

function renderInvitesList(){
  const zone = $("#inv-liste");
  if(!zone) return;
  if(invitesLoadState === "error"){
    zone.innerHTML = `<div class="cc-note deny">${escapeHtml(invitesError || t("error_generic"))}</div>`;
    return;
  }
  if(invitesLoadState !== "ready"){ zone.innerHTML = ""; return; }
  const lignes = INVITES.length
    ? INVITES.map(inv=>`<tr>
        <td>${escapeHtml(inv.nom)} <span class="vide">@${escapeHtml(inv.username)}</span></td>
        <td class="sqn-full">${escapeHtml(inv.discord_id)}</td>
        <td>${escapeHtml(inv.invite_par)}</td>
        <td class="sqn-full">${escapeHtml(invFmtJusqua(inv.jusqua))}</td>
        <td class="sqn-full">${escapeHtml(invFmtEntree(inv.derniere_entree))}</td>
        <td style="white-space:nowrap"><button type="button" class="btn btn-sm cc-act" data-inv-act="prolonger" data-id="${escapeAttr(inv.discord_id)}">${escapeHtml(t("cc_inv_prolonger"))}</button> <button type="button" class="btn btn-sm cc-act" data-inv-act="revoquer" data-id="${escapeAttr(inv.discord_id)}">${escapeHtml(t("cc_inv_revoquer"))}</button></td>
      </tr>`).join("")
    : `<tr class="inv-vide"><td colspan="6"><span class="vide">${escapeHtml(t("cc_inv_vide"))}</span></td></tr>`;
  zone.innerHTML = `<table class="cc-table"><thead><tr>
      <th>${escapeHtml(t("cc_inv_col_invite"))}</th><th>${escapeHtml(t("cc_inv_col_id"))}</th><th>${escapeHtml(t("cc_inv_col_par"))}</th><th>${escapeHtml(t("cc_inv_col_jusqua"))}</th><th>${escapeHtml(t("cc_inv_col_entree"))}</th><th></th>
    </tr></thead><tbody>${lignes}</tbody></table>`;
  ccStampLabels(zone);
  const vide = zone.querySelector(".inv-vide td");
  if(vide) vide.removeAttribute("data-label");
}

async function loadInvites(){
  invitesLoadState = "loading";
  try {
    const d = await apiFetch("/api/command/invites");
    INVITES = d.invites || [];
    invitesLoadState = "ready";
  } catch(e){
    invitesLoadState = "error";
    invitesError = e.message;
  }
  renderInvitesList();
}

function renderInvitesBlock(){
  if(invitesLoadState === "idle"){ loadInvites(); return; }
  renderInvitesList();
}

function invNoteRefus(e){
  $("#inv-note").innerHTML = `<div class="cc-note deny">${escapeHtml((e && e.message) || t("error_generic"))}</div>`;
}

async function invVerifier(){
  const brut = $("#inv-id").value.trim();
  invitesCompte = null;
  try {
    const c = await apiFetch(`/api/command/invites/verifier?discord_id=${encodeURIComponent(brut)}`);
    invitesCompte = c;
    $("#inv-note").innerHTML = `<div class="cc-note">${escFill(t("cc_inv_compte"), {nom: escapeHtml(c.nom), username: escapeHtml(c.username)})} <button type="button" class="btn btn-sm cc-act" data-inv-act="inviter">${escapeHtml(t("cc_inv_inviter"))}</button></div>`;
  } catch(e){ invNoteRefus(e); }
}

async function invInviter(){
  if(!invitesCompte) return;
  try {
    await apiFetch("/api/command/invites", {
      method:"POST", headers:{"Content-Type":"application/json"},
      body: JSON.stringify({discord_id: invitesCompte.discord_id}),
    });
    $("#inv-id").value = "";
    $("#inv-note").innerHTML = "";
    invitesCompte = null;
    await loadInvites();
  } catch(e){ invNoteRefus(e); }
}

async function invAgir(act, id){
  try {
    if(act === "prolonger"){
      await apiFetch(`/api/command/invites/${encodeURIComponent(id)}/prolonger`, {method:"POST"});
    } else {
      await apiFetch(`/api/command/invites/${encodeURIComponent(id)}`, {method:"DELETE"});
    }
    await loadInvites();
  } catch(e){ invNoteRefus(e); }
}

function initInvitesBlock(){
  const bloc = $("#blk-invites");
  if(!bloc) return;
  bloc.addEventListener("click", ev=>{
    const b = ev.target.closest("button");
    if(!b) return;
    if(b.id === "inv-verifier"){ invVerifier(); return; }
    const act = b.dataset.invAct;
    if(act === "inviter") invInviter();
    else if(act === "prolonger" || act === "revoquer") invAgir(act, b.dataset.id);
  });
  $("#inv-id").addEventListener("keydown", ev=>{
    if(ev.key === "Enter"){ ev.preventDefault(); invVerifier(); }
  });
  // Un identifiant retouché n'est plus celui qu'on a vérifié.
  $("#inv-id").addEventListener("input", ()=>{ invitesCompte = null; $("#inv-note").innerHTML = ""; });
}

// Bloc 5 de l'écran Droits -- droits sur le contenu (Lot 3.3, §3).
// STRICTEMENT le gabarit du bloc « Édition des événements du planning »
// (row-plan-roles) : deux rangées de pastilles de rôles Discord, par
// rôle uniquement (aucun octroi nominatif). `data` : réponse complète de
// GET /rights.
function renderContentRightsBlock(data){
  const cr = data.content_rights || {session_edit:{role_ids:[]}, event_edit_any:{role_ids:[]}, campaign_manage:{role_ids:[]}, campaign_delete:{role_ids:[]}};
  const roleDispo = ((COMMAND_DISCORD_ROLES && COMMAND_DISCORD_ROLES.roles) || []).map(r=>({id:r.id, label:r.name}));

  const sessRoleIds = (cr.session_edit && cr.session_edit.role_ids) || [];
  const sessItems = sessRoleIds.map(rid=>({id:rid, label: ccRoleName(rid)}));
  $("#row-sess").innerHTML = ccChipsHtml(sessItems, "sess", roleDispo);

  const evtRoleIds = (cr.event_edit_any && cr.event_edit_any.role_ids) || [];
  const evtItems = evtRoleIds.map(rid=>({id:rid, label: ccRoleName(rid)}));
  $("#row-evt").innerHTML = ccChipsHtml(evtItems, "evt", roleDispo);

  // Lot 3.4 §6 : mêmes patron et gabarit exacts, deux rangées neuves.
  const campRoleIds = (cr.campaign_manage && cr.campaign_manage.role_ids) || [];
  const campItems = campRoleIds.map(rid=>({id:rid, label: ccRoleName(rid)}));
  $("#row-camp").innerHTML = ccChipsHtml(campItems, "camp", roleDispo);

  const campDelRoleIds = (cr.campaign_delete && cr.campaign_delete.role_ids) || [];
  const campDelItems = campDelRoleIds.map(rid=>({id:rid, label: ccRoleName(rid)}));
  $("#row-campdel").innerHTML = ccChipsHtml(campDelItems, "campdel", roleDispo);
}

// Bloc « Accès au module Débriefing », brief du 22 août 2026. STRICTEMENT
// le gabarit des blocs ci-dessus (une seule rangée de pastilles de rôles
// Discord, aucun octroi nominatif) -- mêmes fonctions génériques
// (ccChipsHtml, commandRightsAddMode), aucun mécanisme propre. Bloc à
// part de `renderContentRightsBlock` : une porte de module, pas un droit
// sur un objet (§3 du brief).
function renderDebriefAccessBlock(data){
  const da = data.debrief_access || {role_ids:[]};
  const roleDispo = ((COMMAND_DISCORD_ROLES && COMMAND_DISCORD_ROLES.roles) || []).map(r=>({id:r.id, label:r.name}));
  const items = (da.role_ids||[]).map(rid=>({id:rid, label: ccRoleName(rid)}));
  $("#row-debrief").innerHTML = ccChipsHtml(items, "debrief", roleDispo);
}

// Lot « Les relances » (R7) : le bloc des destinataires. Une rangée de
// pastilles de rôles Discord (gabarit de `renderDebriefAccessBlock`), mêmes
// fonctions génériques, aucun mécanisme propre.
// Lot « Les relances nominatives » (R1) : une seconde rangée, les comptes,
// sur le patron des éditeurs nominatifs du planning (`row-plan-ids`) : les
// profils non archivés de l'annuaire, nommés comme le tableau des membres
// (`callsign`, préfixe retiré) ; un compte qui n'y figure plus (archivé depuis
// son choix) s'affiche par son identifiant avec la mention d'absence.
function renderRelancesBlock(data){
  const rl = data.relances || {role_ids:[], profile_ids:[]};
  const roleDispo = ((COMMAND_DISCORD_ROLES && COMMAND_DISCORD_ROLES.roles) || []).map(r=>({id:r.id, label:r.name}));
  const items = (rl.role_ids||[]).map(rid=>({id:rid, label: ccRoleName(rid)}));
  $("#row-relances").innerHTML = ccChipsHtml(items, "relances", roleDispo);

  const directory = COMMAND_RIGHTS_DIRECTORY || [];
  const idItems = (rl.profile_ids||[]).map(pid=>{
    const found = directory.find(m=>String(m.id)===String(pid));
    return {id:pid, label: found ? callsign(found.name) : (pid + " · " + t("cc_rights_role_absent"))};
  });
  const idDispo = directory.map(m=>({id:m.id, label:callsign(m.name)}));
  $("#row-relances-ids").innerHTML = ccChipsHtml(idItems, "relances-id", idDispo);
}

// Bloc 6 de l'écran Droits -- le tableau de référence des rôles Discord
// (Lot 3.3, §4⑤). Lecture seule, visible à tous. Périmètre et comptes
// viennent de `data.role_reference` (pré-calculé serveur, §4④ : jamais
// déduit côté client -- le front n'a pas les rôles des membres). Les
// OFFICES, en revanche, se déduisent ici des listes déjà connues du
// front (accès, escadrilles, rôle chef, éditeurs du planning, droits sur
// le contenu) -- aucune donnée de membre n'y participe.
function renderRoleReferenceBlock(data){
  const tbody = $("#tb-ref");
  if(!tbody) return;

  const accessSet = new Set((data.app_access && data.app_access.role_ids || []).map(String));
  const chefRoleId = data.chef_role_id != null ? String(data.chef_role_id) : null;
  const planSet = new Set((data.event_editors && data.event_editors.role_ids || []).map(String));
  const cr = data.content_rights || {};
  const sessSet = new Set(((cr.session_edit && cr.session_edit.role_ids) || []).map(String));
  const evtAnySet = new Set(((cr.event_edit_any && cr.event_edit_any.role_ids) || []).map(String));
  const campSet = new Set(((cr.campaign_manage && cr.campaign_manage.role_ids) || []).map(String));
  const campDelSet = new Set(((cr.campaign_delete && cr.campaign_delete.role_ids) || []).map(String));
  const debriefSet = new Set((data.debrief_access && data.debrief_access.role_ids || []).map(String));
  const squadronByRole = {};
  (data.squadrons||[]).forEach(sq=>{
    if(sq.discord_role_id) squadronByRole[String(sq.discord_role_id)] = sq.designation;
  });

  const rows = data.role_reference || [];
  const knownRoles = (COMMAND_DISCORD_ROLES && COMMAND_DISCORD_ROLES.roles) || [];
  const absentIds = [];

  tbody.innerHTML = rows.map(r=>{
    const rid = String(r.role_id);
    const known = knownRoles.some(rr=>String(rr.id)===rid);

    // Colonne 1 : le nom du rôle, td.sqn-role -- même mécanisme déjà
    // existant que `commandSquadronRoleReadHtml()` (écran Escadrilles,
    // 3.2e ①), réemployé ici, pas rebâti (§4⑤).
    let nameCell;
    if(known){
      nameCell = `<td class="sqn-role">${escapeHtml(ccRoleName(rid))}</td>`;
    } else {
      absentIds.push(rid);
      nameCell = `<td class="sqn-role">${escapeHtml(rid)} <span class="absent">${escapeHtml(t("cc_rights_role_absent"))}</span></td>`;
    }

    // Colonne 2 : cellule nue, sans classe -- les offices portent le
    // traitement (.cc-office, R19/R20). Aucune hiérarchie de gravité :
    // seul l'office qui ouvre l'accès porte l'accent (.porte, R20).
    const parts = [];
    if(accessSet.has(rid)) parts.push(`<span class="cc-office porte">${escapeHtml(t("cc_rights_ref_office_access"))}</span>`);
    if(squadronByRole[rid]) parts.push(`<span class="cc-office">${escapeHtml(t("cc_rights_conn_qual_squadron").replace("{squadron}", squadronByRole[rid]))}</span>`);
    if(chefRoleId != null && rid === chefRoleId) parts.push(`<span class="cc-office">${escapeHtml(t("cc_rights_conn_qual_chef"))}</span>`);
    if(planSet.has(rid)) parts.push(`<span class="cc-office">${escapeHtml(t("cc_rights_ref_office_plan"))}</span>`);
    if(sessSet.has(rid)) parts.push(`<span class="cc-office">${escapeHtml(t("cc_rights_ref_office_session"))}</span>`);
    if(evtAnySet.has(rid)) parts.push(`<span class="cc-office">${escapeHtml(t("cc_rights_ref_office_event_any"))}</span>`);
    if(campSet.has(rid)) parts.push(`<span class="cc-office">${escapeHtml(t("cc_rights_ref_office_campaign"))}</span>`);
    if(campDelSet.has(rid)) parts.push(`<span class="cc-office">${escapeHtml(t("cc_rights_ref_office_campaign_delete"))}</span>`);
    if(debriefSet.has(rid)) parts.push(`<span class="cc-office">${escapeHtml(t("cc_rights_ref_office_debrief"))}</span>`);
    const officeCell = `<td>${parts.length ? parts.join(" &middot; ") : `<span class="cc-office">${escapeHtml(t("cc_rights_ref_office_none"))}</span>`}</td>`;

    // Colonne 3 : le compte exact, td.cc-num (R21).
    return `<tr>${nameCell}${officeCell}<td class="cc-num">${r.count}</td></tr>`;
  }).join("");
  ccStampLabels();

  // Seul signalement de ce tableau (§4⑤) : un rôle référencé absent du
  // serveur Discord. Mécanisme déjà porté par la cellule elle-même
  // (span.absent) -- cette note en fait la synthèse quand il y en a une
  // ou plusieurs, silencieuse sinon (aucune hiérarchie de gravité dans
  // la configuration normale).
  $("#ref-notes").innerHTML = absentIds.length
    ? `<div class="cc-note deny">${escapeHtml(t("cc_rights_ref_absent_note").replace("{roles}", absentIds.join(", ")))}</div>`
    : "";
}

// Bloc 4 de l'écran Droits -- accès à l'application (Lot 3.2d, second
// temps). `data` : réponse complète de GET /rights (§6.1).
function renderConnBlock(data){
  const aa = data.app_access || {role_ids:[]};
  const chefRoleId = data.chef_role_id;
  const squadronByRole = {};
  (data.squadrons||[]).forEach(sq=>{
    if(sq.discord_role_id) squadronByRole[String(sq.discord_role_id)] = sq.designation;
  });

  // Qualification d'un rôle (décision 3, §6.1 ; revu Lot 3.2e §7.4, dette
  // 18) : ce qu'il fait EN PLUS d'ouvrir la connexion -- désigne les
  // chefs, ET/OU rattache une escadrille. Ce lot rend `discord_role_id`
  // éditable depuis l'écran Escadrilles : un rôle PEUT désormais cumuler
  // les deux emplois. Retirer de la connexion un rôle qui cumule doit
  // nommer les DEUX conséquences -- taire la chute d'une escadrille serait
  // la plus grave des deux à passer sous silence.
  function qualOf(roleId){
    const rid = String(roleId);
    const quals = [];
    if(chefRoleId != null && rid === String(chefRoleId)) quals.push(t("cc_rights_conn_qual_chef"));
    if(squadronByRole[rid]) quals.push(t("cc_rights_conn_qual_squadron").replace("{squadron}", squadronByRole[rid]));
    return quals.join(" · ");
  }

  const items = (aa.role_ids||[]).map(rid=>({id:rid, label: ccRoleName(rid), qual: qualOf(rid)}));
  const dispo = ((COMMAND_DISCORD_ROLES && COMMAND_DISCORD_ROLES.roles) || []).map(r=>({id:r.id, label:r.name}));
  const discordAvailable = !COMMAND_DISCORD_ROLES || COMMAND_DISCORD_ROLES.available !== false;

  if(commandRightsAddMode === "conn" && !discordAvailable){
    // Serveur Discord injoignable (§7.2) : l'ajout se ferme avec sa
    // mention, les retraits restent possibles, l'écran reste utilisable.
    const chipsOnly = items.map((item,i)=>
      `<span class="cc-chip">${escapeHtml(item.label)}${item.qual?` <span class="qual">${escapeHtml(item.qual)}</span>`:""}<button type="button" data-act="rm-conn" data-i="${i}" aria-label="${escapeHtml(t("cc_rights_chip_remove"))}">×</button></span>`
    ).join("");
    $("#row-conn").innerHTML = chipsOnly +
      ` <span class="cc-hint" style="margin:0">${escapeHtml(t("cc_rights_conn_ko"))}</span>` +
      ` <button type="button" class="btn btn-sm cc-act" data-act="cancel-add-conn">${escapeHtml(t("cc_rights_cancel"))}</button>`;
  } else {
    $("#row-conn").innerHTML = ccChipsHtml(items, "conn", dispo);
    const addBtn = $('#row-conn [data-act="add-conn"]');
    if(addBtn) addBtn.setAttribute("aria-label", t("cc_rights_conn_add"));
  }

  // Mention de source (§7.2) : toujours « géré ici » (lot « rr-socle-proprete », v1.0111 : la lecture du
  // fichier de configuration est retirée).
  $("#conn-src").innerHTML = t("cc_rights_conn_src_app");

  renderConnNotes(data, aa, squadronByRole);
}

// Zone de notes du bloc 4 : confirmation armée d'un retrait, le cas
// échéant. Zone LOCALE au bloc (#conn-notes), distincte de #cc-note-zone
// (blocs 1/2, mécanisme de set-chef/set-rolechef) -- éviter qu'une
// confirmation en cours sur un autre bloc ne s'efface au moindre
// re-rendu de celui-ci, et vice-versa.
//
// Lot 3.3, §4①/②/③ : l'avertissement permanent (chef hors liste) et les
// deux textes de confirmation sur-affirmatifs ("aucun chef ne pourra
// plus entrer" / "plus aucun membre n'entrera") sont RETIRÉS -- le rôle
// chef n'a aucune raison de figurer dans la liste d'accès (c'est un
// TROISIÈME rôle, distinct), la condition de l'avertissement était donc
// vraie en permanence et son affirmation fausse depuis le 3.2d. Rien ne
// remplace l'avertissement permanent : le cas normal est silencieux.
// Les deux textes de confirmation sont remplacés par le COMPTE EXACT
// (§4③, ci-dessous), pré-calculé serveur (`aa.impact`, jamais déduit
// côté client -- le front n'a pas les rôles des membres).
function renderConnNotes(data, aa, squadronByRole){
  const zone = $("#conn-notes");
  if(!zone) return;
  let html = "";

  if(commandRightsConnArmed != null){
    const roleId = commandRightsConnArmed;
    const roleLabel = escapeHtml(ccRoleName(roleId));
    const list = aa.role_ids || [];
    const dernier = list.length <= 1;
    if(dernier){
      html += `<div class="cc-note deny">${t("cc_rights_conn_deny_last").replace("{role}", roleLabel)} ` +
              `<button type="button" class="btn btn-sm cc-act" data-act="conn-cancel">${escapeHtml(t("cc_rights_cancel"))}</button></div>`;
    } else {
      const rid = String(roleId);
      // Compte exact (§4③) : impact(R) = profils NON ADMINISTRATEURS
      // dont roles_snapshot ∩ accès == {R}. Pré-calculé serveur (§4④) --
      // aucune déduction ici, `aa.impact` est un dict {role_id: n}.
      const impact = (aa.impact && aa.impact[rid]) || 0;
      // Ordre impératif (conservé du §7.2 du 3.2d) : le rôle · [impact
      // exact, si >=1] · réassurance administrateur · effet immédiat.
      let phrase = t("cc_rights_conn_confirm").replace("{role}", roleLabel);
      if(impact === 1){
        phrase += t("cc_rights_conn_confirm_impact_one").replace("{n}", impact);
      } else if(impact > 1){
        // impact === 0 : AUCUNE phrase d'impact -- le cas normal est
        // silencieux (§4③). Ne jamais écrire "0 membre concerné" : un
        // compteur bavard réintroduit le bruit que ce lot retire.
        phrase += t("cc_rights_conn_confirm_impact_many").replace("{n}", impact);
      }
      // "L'agissant le porte" (§7.2, 3.2d) : donnée non disponible côté
      // front (session Discord de l'agissant non exposée). Réservé aux
      // administrateurs (§6.2) : la phrase de réassurance reste VRAIE
      // sans condition.
      phrase += t("cc_rights_conn_confirm_mine");
      phrase += t("cc_rights_conn_immediate");
      // Lot « Le Centre au doigt et à la charte » (R4) : la forme commune, en rouge -- retirer un rôle d'accès retire.
      html += ccConfirmHtml({
        titre: t("cc_rights_conn_titre"), texte: phrase, danger: true, err: commandRightsConnErreur, occupe: commandRightsConnEnCours,
        annuler: "conn-cancel", ok: "conn-confirm", libelle: t("cc_rights_confirm_apply"),
      });
    }
  }

  zone.innerHTML = html;
}

function wireCommandRightsEvents(){
  const view = $("#view-cc-droits");
  if(!view || view.dataset.wired) return; // câblage unique -- goCommand() peut être appelé plusieurs fois
  view.dataset.wired = "1";

  view.addEventListener("change", e=>{
    const sel = e.target.closest("select.cc-set"); if(!sel) return;
    const act = sel.dataset.act;
    const value = sel.value || null;

    if(act === "pick-role"){
      if(!value) return;
      commandRightsAddMode = null;
      const ee = COMMAND_RIGHTS.event_editors || {role_ids:[], profile_ids:[]};
      putEventEditors([...(ee.role_ids||[]), value], ee.profile_ids||[]);
      return;
    }
    if(act === "pick-id"){
      if(!value) return;
      commandRightsAddMode = null;
      const ee = COMMAND_RIGHTS.event_editors || {role_ids:[], profile_ids:[]};
      putEventEditors(ee.role_ids||[], [...(ee.profile_ids||[]), value]);
      return;
    }
    if(act === "pick-conn"){
      if(!value) return;
      commandRightsAddMode = null;
      const aa = COMMAND_RIGHTS.app_access || {role_ids:[]};
      putAppAccess([...(aa.role_ids||[]), value]);
      return;
    }
    if(act === "pick-debrief"){
      if(!value) return;
      commandRightsAddMode = null;
      const da = COMMAND_RIGHTS.debrief_access || {role_ids:[]};
      putDebriefAccess([...(da.role_ids||[]), value]);
      return;
    }
    if(act === "pick-relances"){
      if(!value) return;
      commandRightsAddMode = null;
      const rl = COMMAND_RIGHTS.relances || {role_ids:[], profile_ids:[]};
      putRelances([...(rl.role_ids||[]), value], rl.profile_ids||[]);
      return;
    }
    // Lot « Les relances nominatives » (R1) : un compte choisi par son nom.
    if(act === "pick-relances-id"){
      if(!value) return;
      commandRightsAddMode = null;
      const rl = COMMAND_RIGHTS.relances || {role_ids:[], profile_ids:[]};
      putRelances(rl.role_ids||[], [...(rl.profile_ids||[]), value]);
      return;
    }
    if(act === "pick-sess"){
      if(!value) return;
      commandRightsAddMode = null;
      const l = commandContentRightsLists();
      putContentRights([...l.sess, value], l.evt, l.camp, l.campdel);
      return;
    }
    if(act === "pick-evt"){
      if(!value) return;
      commandRightsAddMode = null;
      const l = commandContentRightsLists();
      putContentRights(l.sess, [...l.evt, value], l.camp, l.campdel);
      return;
    }
    if(act === "pick-camp"){
      if(!value) return;
      commandRightsAddMode = null;
      const l = commandContentRightsLists();
      putContentRights(l.sess, l.evt, [...l.camp, value], l.campdel);
      return;
    }
    if(act === "pick-campdel"){
      if(!value) return;
      commandRightsAddMode = null;
      const l = commandContentRightsLists();
      putContentRights(l.sess, l.evt, l.camp, [...l.campdel, value]);
      return;
    }
    if(act === "set-adj"){
      putSquadronDeputy(+sel.dataset.i, value);
      return;
    }
    if(act === "set-rolechef"){
      const previousId = COMMAND_RIGHTS.chef_role_id;
      sel.value = previousId || ""; // le front annonce AVANT d'appeler la route (brief §2)
      if(commandRightsEnCours) return; // addendum 1 : une note occupée agit sur sa propre note, aucune autre ne s'ouvre
      const roleName = value ? ccRoleName(value) : t("cc_rights_role_none");
      showCommandRightsNote(
        t("cc_rights_role_titre"),
        escapeHtml(t("cc_rights_confirm_role").replace("{role}", roleName)),
        !value,
        ()=> putChefRole(value)
      );
      return;
    }
    if(act === "set-chef"){
      const squadronId = +sel.dataset.i;
      const sq = (COMMAND_RIGHTS.squadrons||[]).find(s=>s.id===squadronId);
      if(!sq) return;
      sel.value = sq.leader ? sq.leader.id : ""; // annonce avant appel (geste atomique, brief §2)
      if(commandRightsEnCours) return; // addendum 1 : une note occupée agit sur sa propre note, aucune autre ne s'ouvre
      if(!value){
        const previousName = sq.leader ? callsign(sq.leader.name) : "";
        showCommandRightsNote(
          t("cc_rights_chef_none_titre"),
          escapeHtml(t("cc_rights_confirm_chef_none").replace("{previous}", previousName).replace("{squadron}", sq.designation)),
          true,
          ()=> putSquadronLeader(squadronId, null)
        );
      } else {
        const candidate = (sq.candidates||[]).find(c=>String(c.id)===String(value));
        const name = candidate ? callsign(candidate.name) : value;
        // C1 (correctif 0.9903) : le chef sortant doit être nommé dans la
        // phrase de conséquence quand il y en a un -- aucun rang d'un
        // tiers ne change sans que l'agissant l'ait lu (arbitrage D-4).
        // cc_rights_confirm_chef reste réservée au cas sans chef en poste.
        const msg = sq.leader
          ? t("cc_rights_confirm_chef_takeover")
              .replace("{name}", name)
              .replace("{squadron}", sq.designation)
              .replace("{previous}", callsign(sq.leader.name))
          : t("cc_rights_confirm_chef")
              .replace("{name}", name)
              .replace("{squadron}", sq.designation);
        showCommandRightsNote(
          t("cc_rights_chef_titre"),
          escapeHtml(msg),
          false,
          ()=> putSquadronLeader(squadronId, value)
        );
      }
      return;
    }
  });

  view.addEventListener("click", e=>{
    const b = e.target.closest("[data-act]"); if(!b || b.tagName === "SELECT") return;
    const act = b.dataset.act;

    if(act === "cc-cancel"){ if(commandRightsEnCours) return; clearCommandRightsNote(); renderCommandRights(); return; }
    if(act === "cc-confirm"){
      const fn = commandRightsPending;
      const note = commandRightsNoteCourante;
      if(!fn || !note || commandRightsEnCours) return;
      // Lot « Le Centre au doigt et à la charte » (R5) : la note reste ouverte pendant l'appel ; elle se ferme au succès,
      // et se redessine avec le refus du serveur à l'échec.
      commandRightsEnCours = true;
      ccConfirmOccupe(b);
      (async ()=>{
        try {
          await fn();
          commandRightsEnCours = false;
          clearCommandRightsNote();
        } catch(err){
          commandRightsEnCours = false;
          showCommandRightsNote(note.titre, note.text, note.deny, fn, err.message || t("error_generic"));
        }
      })();
      return;
    }
    if(act === "add-role"){ commandRightsAddMode = "role"; renderCommandRights(); return; }
    if(act === "add-id"){ commandRightsAddMode = "id"; renderCommandRights(); return; }
    if(act === "add-conn"){ commandRightsAddMode = "conn"; renderCommandRights(); return; }
    if(act === "add-debrief"){ commandRightsAddMode = "debrief"; renderCommandRights(); return; }
    if(act === "add-relances"){ commandRightsAddMode = "relances"; renderCommandRights(); return; }
    if(act === "add-relances-id"){ commandRightsAddMode = "relances-id"; renderCommandRights(); return; }
    if(act === "add-sess"){ commandRightsAddMode = "sess"; renderCommandRights(); return; }
    if(act === "add-evt"){ commandRightsAddMode = "evt"; renderCommandRights(); return; }
    if(act === "add-camp"){ commandRightsAddMode = "camp"; renderCommandRights(); return; }
    if(act === "add-campdel"){ commandRightsAddMode = "campdel"; renderCommandRights(); return; }
    if(act === "cancel-add-role" || act === "cancel-add-id" || act === "cancel-add-conn"
       || act === "cancel-add-debrief" || act === "cancel-add-relances" || act === "cancel-add-relances-id"
       || act === "cancel-add-sess" || act === "cancel-add-evt"
       || act === "cancel-add-camp" || act === "cancel-add-campdel"){ commandRightsAddMode = null; renderCommandRights(); return; }

    if(act === "rm-sess"){
      const l = commandContentRightsLists();
      const sessIds = [...l.sess];
      sessIds.splice(+b.dataset.i, 1);
      putContentRights(sessIds, l.evt, l.camp, l.campdel);
      return;
    }
    if(act === "rm-evt"){
      const l = commandContentRightsLists();
      const evtIds = [...l.evt];
      evtIds.splice(+b.dataset.i, 1);
      putContentRights(l.sess, evtIds, l.camp, l.campdel);
      return;
    }
    if(act === "rm-camp"){
      const l = commandContentRightsLists();
      const campIds = [...l.camp];
      campIds.splice(+b.dataset.i, 1);
      putContentRights(l.sess, l.evt, campIds, l.campdel);
      return;
    }
    if(act === "rm-campdel"){
      const l = commandContentRightsLists();
      const campDelIds = [...l.campdel];
      campDelIds.splice(+b.dataset.i, 1);
      putContentRights(l.sess, l.evt, l.camp, campDelIds);
      return;
    }
    // Brief « Accès au module Débriefing » (§5) : retrait IMMÉDIAT, comme
    // rm-camp/rm-campdel -- PAS d'arme/confirme comme rm-conn. Vider
    // cette liste ne ferme aucune porte, aucun filet anti-verrouillage.
    if(act === "rm-debrief"){
      const da = COMMAND_RIGHTS.debrief_access || {role_ids:[]};
      const roleIds = [...(da.role_ids||[])];
      roleIds.splice(+b.dataset.i, 1);
      putDebriefAccess(roleIds);
      return;
    }

    // Lot « Les relances » (R7) : retrait IMMÉDIAT, comme rm-debrief -- vider
    // la liste ne ferme aucune porte, aucun MP ne part.
    if(act === "rm-relances"){
      const rl = COMMAND_RIGHTS.relances || {role_ids:[], profile_ids:[]};
      const roleIds = [...(rl.role_ids||[])];
      roleIds.splice(+b.dataset.i, 1);
      putRelances(roleIds, rl.profile_ids||[]);
      return;
    }
    // Lot « Les relances nominatives » (R1) : retrait immédiat d'un compte,
    // sans filet -- aucune liste n'est à garder non vide.
    if(act === "rm-relances-id"){
      const rl = COMMAND_RIGHTS.relances || {role_ids:[], profile_ids:[]};
      const profileIds = [...(rl.profile_ids||[])];
      profileIds.splice(+b.dataset.i, 1);
      putRelances(rl.role_ids||[], profileIds);
      return;
    }

    if(act === "rm-role"){
      const ee = COMMAND_RIGHTS.event_editors || {role_ids:[], profile_ids:[]};
      const roleIds = [...(ee.role_ids||[])];
      roleIds.splice(+b.dataset.i, 1);
      if(roleIds.length===0 && (ee.profile_ids||[]).length===0){
        showToast(t("cc_rights_deny_last_editor"), "erreur");
        return;
      }
      putEventEditors(roleIds, ee.profile_ids||[]);
      return;
    }
    if(act === "rm-id"){
      const ee = COMMAND_RIGHTS.event_editors || {role_ids:[], profile_ids:[]};
      const profileIds = [...(ee.profile_ids||[])];
      profileIds.splice(+b.dataset.i, 1);
      if(profileIds.length===0 && (ee.role_ids||[]).length===0){
        showToast(t("cc_rights_deny_last_editor"), "erreur");
        return;
      }
      putEventEditors(ee.role_ids||[], profileIds);
      return;
    }

    // Bloc 4 (§7.2) : rm-conn N'APPLIQUE JAMAIS au clic -- il arme et
    // affiche la ligne de conséquence dans #conn-notes (Confirmer /
    // Annuler). Aucun appel réseau avant confirmation. Reclique sur la
    // même puce : désarme (toggle), même patron que le "arme" de la
    // maquette.
    if(act === "rm-conn"){
      const aa = COMMAND_RIGHTS.app_access || {role_ids:[]};
      const roleIds = aa.role_ids || [];
      const roleId = roleIds[+b.dataset.i];
      commandRightsConnErreur = null;
      commandRightsConnArmed = (commandRightsConnArmed === roleId) ? null : roleId;
      renderCommandRights();
      return;
    }
    if(act === "conn-cancel"){ if(commandRightsConnEnCours) return; commandRightsConnArmed = null; commandRightsConnErreur = null; renderCommandRights(); return; }
    if(act === "conn-confirm"){
      const aa = COMMAND_RIGHTS.app_access || {role_ids:[]};
      if(commandRightsConnEnCours) return;
      const armeId = commandRightsConnArmed;
      const roleIds = (aa.role_ids||[]).filter(rid=>rid !== armeId);
      // Lot « Le Centre au doigt et à la charte » (R5) : le rôle reste armé jusqu'à l'issue ; un refus du serveur se lit
      // dans la note.
      commandRightsConnErreur = null;
      commandRightsConnEnCours = true;
      ccConfirmOccupe(b);
      (async ()=>{
        try {
          await putAppAccess(roleIds, true);
          commandRightsConnEnCours = false;
          commandRightsConnArmed = null;
          commandRightsConnErreur = null;
        } catch(err){
          commandRightsConnEnCours = false;
          commandRightsConnErreur = err.message || t("error_generic");
          if(commandRightsConnArmed === armeId) renderCommandRights();
        }
      })();
      return;
    }
  });
}

// Lot 3.2c : bascule entre les écrans du module (Escadrilles / Membres).
// Corrige un défaut latent du 3.2b -- #view-cc-escadrilles ne portait
// aucun basculement JS de sa propre classe "hidden" (le masquage :not()
// de styles.css:984 ne fait que cacher hors module, jamais montrer
// dedans) ; vérifié à l'instrument (Playwright), le rendu restait
// display:none en toute circonstance. Patron de renderDebrief() : une
// liste de vues, .hidden togglée sur celle qui n'est pas active.
/* ===================================================================
   Lot 3.4 « Campagnes » — Centre de Commandement, quatrième écran.
   Patron : #view-cc-escadrilles (3.2e ①) pour le gabarit table + bloc de
   formulaire ; ce dernier sert ICI à la fois la création ET l'édition
   (§3, « un seul bloc ») -- bascule pilotée par `commandCampaignsEditId`,
   jamais une modale, jamais un second formulaire. Gating par capacité
   globale (`ME.capabilities`), pas par appartenance d'escadrille : une
   campagne n'a pas de notion d'escadrille.
   =================================================================== */
let commandCampaignsLoadState = "idle"; // idle | loading | ready | error
let commandCampaignsError = null;
let COMMAND_CAMPAIGNS = null;
let commandCampaignsEditId = null;   // id de la campagne en édition, ou null (bloc en mode création)
let commandCampaignsArmed = null;    // id de la campagne armée pour suppression, ou null
let commandCampaignsEnCours = false;  // Addendum 1 (A1) : vrai du clic sur « Supprimer » à l'issue de l'appel ; la note est dessinée occupée
let commandCampaignsErreur = null;   // Lot « Le Centre au doigt et à la charte » (R5) : le refus du serveur, dans la note ; remis à null à chaque armement, annulation ou succès

function commandCanManageCampaigns(){
  return !!(ME && (ME.capabilities||[]).includes("campaign.manage"));
}
function commandCanDeleteCampaigns(){
  return !!(ME && (ME.capabilities||[]).includes("campaign.delete"));
}

async function loadCommandCampaigns(){
  commandCampaignsLoadState = "loading";
  commandCampaignsError = null;
  renderCommandCampaigns();
  try {
    const data = await apiFetch("/api/command/campaigns");
    COMMAND_CAMPAIGNS = data.campaigns || [];
    commandCampaignsLoadState = "ready";
  } catch(e){
    commandCampaignsLoadState = "error";
    commandCampaignsError = e.message || t("error_generic");
  }
  renderCommandCampaigns();
}

function ensureCommandCampaignsLoaded(){
  if(commandCampaignsLoadState === "ready" || commandCampaignsLoadState === "loading"){
    renderCommandCampaigns();
  } else {
    loadCommandCampaigns();
  }
}

// Squelette de chargement -- six largeurs distinctes (jamais uniformes,
// dette 15 déjà soldée ailleurs dans ce module, cf. Lot 3.3 §6).
function commandCampaignsSkeletonRowsHtml(){
  const widths = ["45%","35%","30%","25%","20%","40%"];
  const row = `<tr>${widths.map(w=>`<td><span class="skel" style="width:${w}"></span></td>`).join("")}</tr>`;
  return row.repeat(4);
}

function commandCampaignRowHtml(c){
  const canManage = commandCanManageCampaigns();
  const canDelete = commandCanDeleteCampaigns();
  const statusCell = c.status === "close"
    ? `<span class="cc-office">${escapeHtml(t("cc_camp_status_close"))}</span>`
    : escapeHtml(t("cc_camp_status_en_cours"));
  const armedHere = commandCampaignsArmed === c.id;
  const acts = [];
  if(canManage){
    acts.push(`<button type="button" class="btn btn-sm cc-act" data-act="camp-edit" data-id="${escapeAttr(c.id)}">${escapeHtml(t("cc_camp_act_edit"))}</button>`);
  }
  if(canDelete){
    acts.push(`<button type="button" class="btn btn-sm cc-act${armedHere?" arm":""}" data-act="camp-delete" data-id="${escapeAttr(c.id)}">${escapeHtml(t("cc_camp_act_delete"))}</button>`);
  }
  return `<tr>
    <td>${escapeHtml(c.name)}</td>
    <td class="sqn-role">${escapeHtml(simLabel(c.sim))}</td>
    <td>${escapeHtml(c.map_name || "—")}</td>
    <td>${statusCell}</td>
    <td class="cc-num">${c.mission_count}</td>
    <td>${acts.length ? `<div class="cc-row">${acts.join("")}</div>` : "—"}</td>
  </tr>`;
}

// Zone de conséquence (§7) -- le refus chiffré (≥1 mission) ou la
// confirmation simple (0 mission), sous le tableau. Même gabarit que
// `showCommandRightsNote`/`.cc-note`(+.deny) déjà en feuille.
function renderCommandCampaignsNote(){
  const zone = $("#cc-camp-note-zone");
  if(!zone) return;
  if(!commandCampaignsArmed){ zone.innerHTML = ""; return; }
  const c = (COMMAND_CAMPAIGNS||[]).find(x=>x.id===commandCampaignsArmed);
  if(!c){ zone.innerHTML = ""; return; }

  if(c.mission_count > 0){
    zone.innerHTML = `<div class="cc-note deny">${escapeHtml(t("cc_camp_delete_deny").replace("{name}", c.name).replace("{count}", c.mission_count))}
      <button type="button" class="btn btn-sm cc-act" data-act="camp-delete-close">${escapeHtml(t("cc_camp_note_close"))}</button></div>`;
  } else {
    zone.innerHTML = ccConfirmHtml({
      titre: t("cc_camp_delete_titre"), texte: escapeHtml(t("cc_camp_delete_confirm").replace("{name}", c.name)),
      danger: true, err: commandCampaignsErreur, occupe: commandCampaignsEnCours,
      annuler: "camp-delete-cancel", ok: "camp-delete-ok", libelle: t("cc_camp_act_delete"),
      attrs: ` data-id="${escapeAttr(c.id)}"`,
    });
  }
}

// Bloc de création/édition (§3) -- masqué sans `campaign.manage`, et
// pendant le chargement (même patron que `renderCommandSquadronsCreate`).
function renderCommandCampaignsForm(){
  const block = $("#cc-camp-create");
  if(!block) return;
  const show = commandCanManageCampaigns() && commandCampaignsLoadState === "ready";
  block.classList.toggle("hidden", !show);
  if(!show) return;

  const editing = (COMMAND_CAMPAIGNS||[]).find(c=>c.id===commandCampaignsEditId) || null;

  $("#cc-camp-sim").innerHTML = campaignSimOptionsHtml(editing ? editing.sim : "dcs");
  $("#cc-camp-form-title").textContent = editing
    ? t("cc_camp_edit_title").replace("{name}", editing.name)
    : t("cc_camp_create_title");
  $("#cc-camp-form-hint").textContent = editing ? t("cc_camp_edit_hint") : t("cc_camp_create_hint");
  $("#cc-camp-submit").textContent = editing ? t("cc_camp_submit_save") : t("cc_camp_submit_create");
  $("#cc-camp-cancel").classList.toggle("hidden", !editing);

  $("#cc-camp-name").value = editing ? editing.name : "";
  $("#cc-camp-sim").value = editing ? editing.sim : "dcs";
  $("#cc-camp-theater").value = editing ? (editing.map_name || "") : "";
  $("#cc-camp-status").value = editing ? editing.status : "en_cours";
  $("#cc-camp-desc").value = editing ? (editing.description || "") : "";

  // Verrou simulateur (§5) : désactivé, jamais masqué, dès qu'au moins
  // une mission est rattachée -- la raison est chiffrée en dessous.
  const locked = !!(editing && editing.mission_count > 0);
  $("#cc-camp-sim").disabled = locked;
  $("#cc-camp-form-note").innerHTML = locked
    ? `<div class="cc-note deny">${escapeHtml(t("cc_camp_sim_locked").replace("{count}", editing.mission_count))}</div>`
    : "";
}

function renderCommandCampaigns(){
  const table = $("#cc-camp-table");
  const tbody = $("#cc-camp-tbody");
  const wrap = table ? table.closest(".cc-wrap") : null;
  const emptyEl = $("#cc-camp-empty");
  const errorEl = $("#cc-camp-error");
  if(!table || !tbody || !wrap || !emptyEl || !errorEl) return;

  wrap.classList.add("hidden");
  emptyEl.classList.add("hidden");
  errorEl.classList.add("hidden");

  if(commandCampaignsLoadState === "loading"){
    wrap.classList.remove("hidden");
    tbody.innerHTML = commandCampaignsSkeletonRowsHtml();
    ccStampLabels();
    renderCommandCampaignsForm();
    return;
  }
  if(commandCampaignsLoadState === "error"){
    errorEl.classList.remove("hidden");
    renderCommandCampaignsForm();
    return;
  }
  const list = COMMAND_CAMPAIGNS || [];
  if(list.length === 0){
    emptyEl.classList.remove("hidden");
    renderCommandCampaignsNote();
    renderCommandCampaignsForm();
    return;
  }
  wrap.classList.remove("hidden");
  tbody.innerHTML = list.map(commandCampaignRowHtml).join("");
  ccStampLabels();
  renderCommandCampaignsNote();
  renderCommandCampaignsForm();
}

function commandCampaignsResetEdit(){
  commandCampaignsEditId = null;
}

async function upsertCommandCampaign(body){
  return apiFetch("/api/command/campaigns", {
    method: "POST", headers: {"Content-Type": "application/json"},
    body: JSON.stringify(body),
  });
}

async function deleteCommandCampaign(campaignId){
  return apiFetch(`/api/command/campaigns/${campaignId}`, {method: "DELETE"});
}

function wireCommandCampaignsEvents(){
  const view = $("#view-cc-campagnes");
  if(!view || view.dataset.wired) return;
  view.dataset.wired = "1";

  view.addEventListener("click", e=>{
    const b = e.target.closest("[data-act]");
    if(!b || b.tagName === "SELECT") return;
    const act = b.dataset.act;
    const id = b.dataset.id || null;

    if(act === "camp-edit"){
      commandCampaignsArmed = null;
      commandCampaignsErreur = null;
      commandCampaignsEditId = id;
      renderCommandCampaigns();
      return;
    }
    if(act === "camp-cancel"){
      commandCampaignsResetEdit();
      renderCommandCampaigns();
      return;
    }
    if(act === "camp-delete"){
      commandCampaignsResetEdit();
      commandCampaignsErreur = null;
      commandCampaignsArmed = (commandCampaignsArmed === id) ? null : id;
      renderCommandCampaigns();
      return;
    }
    if(act === "camp-delete-cancel" || act === "camp-delete-close"){
      if(commandCampaignsEnCours) return; // addendum 1 : la note est occupée
      commandCampaignsArmed = null;
      commandCampaignsErreur = null;
      renderCommandCampaigns();
      return;
    }
    if(act === "camp-delete-ok"){
      const armedId = commandCampaignsArmed;
      if(!armedId) return;
      if(commandCampaignsEnCours) return;
      commandCampaignsErreur = null;
      commandCampaignsEnCours = true;
      ccConfirmOccupe(b);
      (async ()=>{
        try {
          await deleteCommandCampaign(armedId);
          commandCampaignsEnCours = false;
          commandCampaignsArmed = null;
          commandCampaignsErreur = null;
          await loadCommandCampaigns();
        } catch(err){
          // Lot « Le Centre au doigt et à la charte » (R5) : l'état armé reste, le refus du serveur est dans la note.
          commandCampaignsEnCours = false;
          commandCampaignsErreur = err.message || t("error_generic");
          if(commandCampaignsArmed === armedId) renderCommandCampaigns();
        }
      })();
      return;
    }
    if(act === "camp-submit"){
      const name = $("#cc-camp-name").value.trim();
      const noteEl = $("#cc-camp-form-note");
      if(!name){
        if(noteEl) noteEl.innerHTML = `<div class="cc-note deny">${escapeHtml(t("cc_camp_create_deny_name"))}</div>`;
        return;
      }
      const body = {
        name,
        sim: $("#cc-camp-sim").value || "dcs",
        map_name: $("#cc-camp-theater").value.trim(),
        status: $("#cc-camp-status").value || "en_cours",
        description: $("#cc-camp-desc").value.trim(),
      };
      if(commandCampaignsEditId) body.id = commandCampaignsEditId;
      (async ()=>{
        try {
          await upsertCommandCampaign(body);
          commandCampaignsResetEdit();
          await loadCommandCampaigns();
        } catch(err){
          if(noteEl) noteEl.innerHTML = `<div class="cc-note deny">${escapeHtml(err.message || t("error_generic"))}</div>`;
        }
      })();
      return;
    }
  });
}


/* ===================================================================
   Lot « L'écran Escadre du Centre » — Centre de Commandement, l'onglet
   Escadre : l'identité de l'escadre (désignation, nom complet, période,
   sigle, tag, emblème). Patron : l'écran Campagnes pour les états, le geste
   « écusson » des escadrilles pour l'emblème. Les administrateurs modifient ;
   les autres porteurs de l'accès au Centre voient la fiche en lecture seule.
   Enregistrer n'écrit rien : il pose une confirmation ; Appliquer écrit.
   =================================================================== */
let commandEscadreLoadState = "idle"; // idle | loading | ready | error
let COMMAND_ESCADRE = null;           // {designation, full_name, period, sigle, tag, emblem_sha, you:{is_admin}}
let commandEscadreForm = null;        // valeurs saisies + `linked` (le tag suit la désignation)
let commandEscadreNote = null;        // null | {kind:"confirm"|"emblem"|"msg", ...}

// Lot « Le Centre de Commandement dit ce qu'il fait » (R11.6) : `max` = la borne du serveur
// (`_WING_LIMITS` et `_SIGLE_RE` de `app/command/api.py`), posée en `maxlength`.
const ESC_FIELDS = [
  {key:"designation", id:"designation", lab:"cc_esc_f_designation", size:22, max:40},
  {key:"full_name",   id:"nom",         lab:"cc_esc_f_fullname",    size:40, max:120},
  {key:"period",      id:"periode",     lab:"cc_esc_f_period",      size:30, max:60, aide:"period"},
  {key:"sigle",       id:"sigle",       lab:"cc_esc_f_sigle",       size:8,  max:12, aide:"sigle"},
  {key:"tag",         id:"tag",         lab:"cc_esc_f_tag",         size:22, max:40, aide:"tag"},
];

// Remplace `{clé}` par sa valeur -- par fonction, jamais par chaîne (une saisie peut contenir `$&`).
function escFill(text, map){
  return text.replace(/\{(\w+)\}/g, (m, k)=> Object.prototype.hasOwnProperty.call(map, k) ? map[k] : m);
}

function commandEscadreIsAdmin(){
  return !!(COMMAND_ESCADRE && COMMAND_ESCADRE.you && COMMAND_ESCADRE.you.is_admin);
}

// Valeurs d'un champ comparables : rognées ; le sigle en capitales ; NULL = vide.
function escNorm(key, v){
  const x = (v == null ? "" : String(v)).trim();
  return key === "sigle" ? x.toUpperCase() : x;
}

function commandEscadreFormLoad(){
  const w = COMMAND_ESCADRE || {};
  commandEscadreForm = {
    designation: w.designation || "",
    full_name: w.full_name || "",
    period: w.period || "",
    sigle: w.sigle || "",
    tag: w.tag || "",
    // Le tag suit la désignation tant qu'on ne l'a pas touché : lié si, au chargement, il l'égale.
    linked: (w.tag || "") === (w.designation || ""),
  };
}

function commandEscadreChanges(){
  const w = COMMAND_ESCADRE || {}, f = commandEscadreForm || {};
  return ESC_FIELDS.filter(F => escNorm(F.key, f[F.key]) !== escNorm(F.key, w[F.key]));
}

async function loadCommandEscadre(){
  commandEscadreLoadState = "loading";
  renderCommandEscadre();
  try {
    COMMAND_ESCADRE = await apiFetch("/api/command/wing");
    commandEscadreFormLoad();
    commandEscadreNote = null;
    commandEscadreLoadState = "ready";
  } catch(e){
    commandEscadreLoadState = "error";
  }
  renderCommandEscadre();
}

function ensureCommandEscadreLoaded(){
  if(commandEscadreLoadState === "ready" || commandEscadreLoadState === "loading"){
    renderCommandEscadre();
  } else {
    loadCommandEscadre();
  }
}

// Aide d'un champ, avec la valeur EN COURS DE SAISIE (vue administrateur) ou enregistrée (lecture seule).
function commandEscadreAideText(kind, vals){
  if(kind === "period") return t("cc_esc_h_period");
  if(kind === "sigle"){
    const sg = escNorm("sigle", vals.sigle);
    // Sans sigle, la référence perd son « {sigle}/ » (comme `mrefText`).
    return t("cc_esc_h_sigle").replace(sg ? "{sigle}" : "{sigle}/", () => sg);
  }
  const tg = escNorm("tag", vals.tag);
  return escFill(t("cc_esc_h_tag"), {tag: tg || "…"});
}

function renderCommandEscadre(){
  const box = $("#cc-esc-fiche");
  if(!box) return;
  if(commandEscadreLoadState === "loading" || commandEscadreLoadState === "idle"){
    const rows = ["70%","90%","60%","85%","75%"].map((w,i)=>`<span class="skel" style="width:${w}"></span><span class="skel" style="width:${i%2?"55%":"80%"}"></span>`).join("");
    box.innerHTML = `<div class="cc-fiche">${rows}</div>`;
    renderCommandEscadreNote();
    return;
  }
  if(commandEscadreLoadState === "error"){
    box.innerHTML = `<div class="cc-state"><div>${escapeHtml(t("cc_esc_error"))}</div><div class="cc-state-act"><button type="button" class="btn btn-sm" data-act="esc-retry">${escapeHtml(t("cc_camp_retry"))}</button></div></div>`;
    renderCommandEscadreNote();
    return;
  }

  const w = COMMAND_ESCADRE, admin = commandEscadreIsAdmin();
  const vals = admin ? commandEscadreForm : w;
  const dirty = admin && commandEscadreChanges().length > 0;
  const champ = F => {
    const lab = `<label for="cc-esc-${F.id}">${escapeHtml(t(F.lab))}</label>`;
    const val = admin
      ? `<input class="cc-set" id="cc-esc-${F.id}" type="text" size="${F.size}" maxlength="${F.max}" data-act="esc-f" data-f="${F.key}" value="${escapeAttr(vals[F.key] || "")}">`
      : `<span class="cc-fiche-val">${escapeHtml(w[F.key] || "—")}</span>`;
    const aide = F.aide ? `<span class="cc-hint cc-fiche-aide" id="cc-esc-h-${F.aide}">${escapeHtml(commandEscadreAideText(F.aide, vals))}</span>` : "";
    return lab + val + aide;
  };
  const emb = `<img class="cc-esc-emb" src="${escapeAttr(wingEmblemUrl(w.emblem_sha))}" alt="${escapeAttr(t("cc_esc_emblem_alt"))}" data-wing-emblem>`;
  const emblemBtn = admin
    ? `<label class="btn btn-sm cc-act">${escapeHtml(t("cc_esc_emblem_btn"))}<input type="file" class="hidden" accept="image/png,image/webp" data-act="esc-emblem-pick"></label>`
    : "";
  box.innerHTML = `
    <div class="cc-esc-tete">
      ${emb}
      <div>
        <div class="cc-esc-nom">${escapeHtml(w.designation)}</div>
        <div class="cc-hint" style="margin:.15rem 0 .5rem">${escapeHtml(w.full_name || "")}</div>
        ${emblemBtn}
      </div>
    </div>
    <h3 class="cc-sub">${escapeHtml(t("cc_esc_id_title"))}</h3>
    <p class="cc-hint">${escapeHtml((admin ? t("cc_esc_admin_only") + " " : "") + t("cc_esc_id_hint"))}</p>
    <div class="cc-fiche">${ESC_FIELDS.map(champ).join("")}</div>
    ${admin ? `<div class="cc-row" style="margin-top:.9rem">
      <button type="button" class="btn btn-sm cc-act" id="cc-esc-save" data-act="esc-save"${dirty ? "" : " disabled"}>${escapeHtml(t("cc_esc_save"))}</button>
      ${commandEscadreNote && commandEscadreNote.kind === "confirm" ? `<button type="button" class="btn btn-sm cc-act" data-act="esc-cancel">${escapeHtml(t("cc_rights_cancel"))}</button>` : ""}
    </div>` : ""}`;
  renderCommandEscadreNote();
}

// Mise à jour EN PLACE à chaque frappe (jamais un rendu complet : le champ perdrait le focus).
function syncCommandEscadreLive(){
  const f = commandEscadreForm;
  if(!f) return;
  const tagEl = $("#cc-esc-tag");
  if(tagEl && tagEl.value !== f.tag) tagEl.value = f.tag;
  [["sigle","sigle"],["tag","tag"]].forEach(([id, kind])=>{
    const el = $("#cc-esc-h-"+id);
    if(el) el.textContent = commandEscadreAideText(kind, f);
  });
  const save = $("#cc-esc-save");
  if(save) save.disabled = commandEscadreChanges().length === 0;
}

function renderCommandEscadreNote(){
  const zone = $("#cc-esc-note-zone");
  if(!zone) return;
  const n = commandEscadreNote;
  if(!n || (commandEscadreLoadState !== "ready")){ zone.innerHTML = ""; return; }
  if(n.kind === "msg"){
    const text = n.key ? t(n.key) : n.text;
    zone.innerHTML = `<div class="cc-note${n.deny ? " deny" : ""}">${escapeHtml(text)}</div>`;
    return;
  }
  if(n.kind === "confirm"){
    const items = n.changes.map(c => escFill(t("cc_esc_change_item"), {
      field: t(c.lab), from: c.from || "—", to: c.to || "—",
    }));
    let html = escapeHtml(escFill(t("cc_esc_confirm"), {changes: items.join(" ; ")}));
    if(n.tagChanged){
      // « Le tag change : » (jusqu'au premier deux-points du texte du dictionnaire) se pose en gras.
      const tpl = t("cc_esc_confirm_tag");
      const i = tpl.indexOf(":") + 1;
      const head = tpl.slice(0, i), rest = escFill(tpl.slice(i), {old: n.oldTag});
      html += " <b>" + escapeHtml(head) + "</b>" + escapeHtml(rest);
    }
    zone.innerHTML = ccConfirmHtml({
      titre: t("cc_esc_titre"), texte: html, err: n.erreur || null, occupe: !!n.enCours,
      annuler: "esc-cancel", ok: "esc-apply", libelle: t("cc_rights_confirm_apply"),
    });
    return;
  }
  if(n.kind === "emblem"){
    // Refus client (politesse -- le serveur revérifie tout) : .cc-note.deny, l'emblème en place ne bouge pas.
    if(n.denyKey){
      const msg = t(n.denyKey).replace("{name}", () => n.fileName).replace("{size}", () => n.denySize || "");
      zone.innerHTML = `<div class="cc-note deny">${escapeHtml(msg)}
        <button type="button" class="btn btn-sm cc-act" data-act="esc-emblem-cancel">${escapeHtml(t("cc_rights_cancel"))}</button></div>`;
      return;
    }
    if(!n.previewSrc){ zone.innerHTML = ""; return; } // aperçu pas encore prêt
    const preview = t("cc_sqn_crest_preview").replace("{dims}", `${n.sourceW} × ${n.sourceH} px`);
    zone.innerHTML = ccConfirmHtml({
      titre: t("cc_esc_emblem_titre"), texte: escapeHtml(preview),
      choix: `<img class="sqn-crest lg" src="${escapeAttr(n.previewSrc)}" alt="${escapeAttr(t("cc_esc_emblem_alt"))}">`,
      err: n.erreur || null, occupe: !!n.enCours,
      annuler: "esc-emblem-cancel", ok: "esc-emblem-apply", libelle: t("cc_esc_emblem_apply"),
    });
  }
}

// Après une écriture : `/api/me` se relit (identité, préfixes de pseudos), puis l'identité est
// réappliquée dans toute l'application, sans rechargement.
async function commandEscadreRefreshIdentity(written){
  try {
    await loadMe();
  } catch(e){
    if(ME) ME.wing = Object.assign({}, written); // `/api/me` injoignable : la réponse d'écriture fait foi
  }
  applyWingIdentity();
}

function handleCommandEscadreEmblemPick(input){
  const file = input.files && input.files[0];
  if(!file) return;
  const fileName = file.name;
  input.value = "";

  const deny = (denyKey, extra) => {
    commandEscadreNote = Object.assign({kind:"emblem", denyKey, fileName, previewSrc:null}, extra || {});
    renderCommandEscadre();
  };
  if(/\.svgz?$/i.test(fileName) || file.type === "image/svg+xml") return deny("cc_sqn_crest_deny_vector");
  if(file.size > 2 * 1024 * 1024) return deny("cc_sqn_crest_deny_weight", {denySize: (file.size / (1024 * 1024)).toFixed(1)});
  if(!/^image\/(png|webp)$/.test(file.type)) return deny("cc_sqn_crest_deny_format");

  const note = {kind:"emblem", denyKey:null, fileName, previewSrc:null, sourceW:null, sourceH:null, fileBlob:file};
  commandEscadreNote = note;
  renderCommandEscadre();
  (async ()=>{
    try {
      const dataUrl = await crestReadFileAsDataUrl(file);
      const dims = await crestLoadImageDims(dataUrl);
      if(commandEscadreNote !== note) return; // annulé entretemps
      note.previewSrc = dataUrl; note.sourceW = dims.w; note.sourceH = dims.h;
      renderCommandEscadreNote();
    } catch(err){
      if(commandEscadreNote !== note) return;
      note.denyKey = "cc_sqn_crest_deny_broken";
      renderCommandEscadreNote();
    }
  })();
}

function wireCommandEscadreEvents(){
  const view = $("#view-cc-escadre");
  if(!view || view.dataset.wired) return; // câblage unique
  view.dataset.wired = "1";

  view.addEventListener("input", e=>{
    const el = e.target.closest('input[data-act="esc-f"]');
    if(!el || !commandEscadreForm) return;
    const f = commandEscadreForm, key = el.dataset.f;
    f[key] = el.value;
    if(key === "designation" && f.linked) f.tag = el.value; // le tag suit la désignation
    if(key === "tag") f.linked = false;                      // une frappe dans le tag rompt le lien
    // Une confirmation déjà posée ne vaut plus pour ce qui est à l'écran.
    if(commandEscadreNote && commandEscadreNote.kind === "confirm"){
      commandEscadreNote = null;
      renderCommandEscadre();
      const again = $("#cc-esc-" + (ESC_FIELDS.find(F=>F.key===key) || {}).id);
      if(again){ again.focus(); try { again.setSelectionRange(again.value.length, again.value.length); } catch(_){} }
      return;
    }
    syncCommandEscadreLive();
  });

  view.addEventListener("change", e=>{
    const pick = e.target.closest('input[type="file"][data-act="esc-emblem-pick"]');
    if(pick) handleCommandEscadreEmblemPick(pick);
  });

  view.addEventListener("click", e=>{
    const b = e.target.closest("[data-act]");
    if(!b || b.tagName === "INPUT") return;
    const act = b.dataset.act;

    if(act === "esc-retry"){ loadCommandEscadre(); return; }

    if(act === "esc-save"){
      if(commandEscadreNote && commandEscadreNote.enCours) return; // v1.0099 : la note est occupée (PATCH en cours)
      const changes = commandEscadreChanges();
      if(!changes.length) return;
      const w = COMMAND_ESCADRE, f = commandEscadreForm;
      const body = {};
      changes.forEach(F => { body[F.key] = f[F.key].trim(); });
      commandEscadreNote = {
        kind: "confirm",
        body,
        changes: changes.map(F => ({lab: F.lab, from: escNorm(F.key, w[F.key]), to: escNorm(F.key, f[F.key])})),
        tagChanged: changes.some(F => F.key === "tag"),
        oldTag: w.tag || "",
      };
      renderCommandEscadre();
      return;
    }

    if(act === "esc-cancel"){
      if(commandEscadreNote && commandEscadreNote.enCours) return; // addendum 1 : la note est occupée
      commandEscadreFormLoad(); // rend le formulaire chargé
      commandEscadreNote = null;
      renderCommandEscadre();
      return;
    }

    if(act === "esc-apply"){
      const n = commandEscadreNote;
      if(!n || n.kind !== "confirm") return;
      if(n.enCours) return;
      n.erreur = null;
      n.enCours = true;
      ccConfirmOccupe(b);
      (async ()=>{
        try {
          const data = await apiFetch("/api/command/wing", {
            method: "PATCH",
            headers: {"Content-Type": "application/json"},
            body: JSON.stringify(n.body),
          });
          n.enCours = false;
          COMMAND_ESCADRE = Object.assign({}, COMMAND_ESCADRE, data);
          commandEscadreFormLoad();
          commandEscadreNote = {kind:"msg", key:"cc_esc_saved"};
          await commandEscadreRefreshIdentity(data); // rejoue setLang, donc re-rend l'écran
          renderCommandEscadre();
        } catch(err){
          // Lot « Le Centre au doigt et à la charte » (R5) : un 422 s'écrit avec le `detail` du serveur dans la note, qui
          // reste armée ; la saisie reste.
          n.enCours = false;
          n.erreur = err.message || t("error_generic");
          if(commandEscadreNote === n) renderCommandEscadreNote();
        }
      })();
      return;
    }

    if(act === "esc-emblem-cancel"){
      if(commandEscadreNote && commandEscadreNote.enCours) return; // addendum 1 : la note est occupée
      commandEscadreNote = null;
      renderCommandEscadre();
      return;
    }

    if(act === "esc-emblem-apply"){
      const n = commandEscadreNote;
      if(!n || n.kind !== "emblem" || !n.fileBlob) return;
      if(n.enCours) return;
      n.erreur = null;
      n.enCours = true;
      ccConfirmOccupe(b);
      (async ()=>{
        try {
          const fd = new FormData();
          fd.append("file", n.fileBlob);
          const data = await apiFetch("/api/command/wing/emblem", {method: "PUT", body: fd});
          n.enCours = false;
          COMMAND_ESCADRE = Object.assign({}, COMMAND_ESCADRE, {emblem_sha: data.emblem_sha});
          commandEscadreNote = {kind:"msg", key:"cc_esc_emblem_done"};
          await commandEscadreRefreshIdentity(data);
          renderCommandEscadre();
        } catch(err){
          n.enCours = false;
          n.erreur = err.message || t("error_generic");
          if(commandEscadreNote === n) renderCommandEscadreNote();
        }
      })();
      return;
    }
  });
}


/* ===================================================================
   Lot « Les référentiels : types et armes » -- l'écran Référentiels du
   Centre. À chaque clé DCS d'unité ou d'arme, un libellé ; à chaque type, sa
   catégorie (automatique, ou forcée). Les administrateurs modifient, importent
   et exportent ; les autres porteurs de l'accès au Centre lisent (et
   exportent). « Modifier » ouvre UNE ligne sur place ; l'import montre son
   bilan avant d'écrire (appliquer=0), puis écrit (appliquer=1).
   =================================================================== */
let commandRefLoadState = "idle"; // idle | loading | ready | error
let COMMAND_REF = null;           // {types, armes, categories, you:{is_admin}}
let commandRefFiltre = {q: "", sans: false};
let commandRefEdit = null;        // null | {liste:"types"|"armes", cle, libelle, categorie:""|<catégorie>}
let commandRefNote = null;        // null | {kind:"msg", key|text, vars, deny} | {kind:"import", fichier, bilan, contenu}

const REF_CONTRAT = "readyroom_referentiel_types_armes";

function commandRefIsAdmin(){
  return !!(COMMAND_REF && COMMAND_REF.you && COMMAND_REF.you.is_admin);
}

async function loadCommandRef(){
  commandRefLoadState = "loading";
  renderCommandRef();
  try {
    COMMAND_REF = await apiFetch("/api/command/referentiels");
    commandRefLoadState = "ready";
  } catch(e){
    commandRefLoadState = "error";
  }
  renderCommandRef();
}

function ensureCommandRefLoaded(){
  if(commandRefLoadState === "ready" || commandRefLoadState === "loading"){
    renderCommandRef();
  } else {
    loadCommandRef();
  }
}

// Relit la liste sans repasser par l'état « chargement » (après une écriture) et rend les
// libellés à tous les écrans.
async function reloadCommandRef(){
  try {
    COMMAND_REF = await apiFetch("/api/command/referentiels");
    commandRefLoadState = "ready";
  } catch(e){
    commandRefLoadState = "error";
  }
  await refreshLibelles();
  renderCommandRef();
}

// Les libellés se relisent, puis les écrans du Débrief déjà ouverts se redessinent (comme setLang).
async function refreshLibelles(){
  await loadLibelles();
  if(DEBRIEF_SESSIONS) renderMissions();
  if(CURRENT_SESSION && sessionDetailLoadState === "ready") renderSession();
  if(CURRENT_FLIGHT  && flightDetailLoadState  === "ready") renderFlight();
  if(dossierLoadState === "ready") renderPilotes();
  if(campagnesLoadState !== "idle") renderCampagnes();
  if(CURRENT_CAMPAIGN_ID && campagneLoadState[CURRENT_CAMPAIGN_ID]) renderCampagne();
}

function commandRefMatch(e){
  const q = commandRefFiltre.q.trim().toLowerCase();
  if(commandRefFiltre.sans && e.libelle) return false;
  if(!q) return true;
  return (e.cle + " " + (e.libelle || "")).toLowerCase().includes(q);
}

function commandRefSansLibelle(){
  if(!COMMAND_REF) return 0;
  return COMMAND_REF.types.filter(e => !e.libelle).length + COMMAND_REF.armes.filter(e => !e.libelle).length;
}

function commandRefLigne(liste, e, admin){
  const cle = `<code class="ref-cle">${escapeHtml(e.cle)}</code>`;
  const isTypes = liste === "types";
  const ed = commandRefEdit;
  if(admin && ed && ed.liste === liste && ed.cle === e.cle){
    const cats = COMMAND_REF.categories.map(c => `<option value="${escapeAttr(c)}"${ed.categorie === c ? " selected" : ""}>${escapeHtml(catLabel(c))}</option>`).join("");
    const auto = `<option value=""${ed.categorie === "" ? " selected" : ""}>${escapeHtml(escFill(t("cc_ref_auto"), {cat: catLabel(e.categorie_auto)}))}</option>`;
    return `<tr class="cc-you" data-liste="${liste}"><td>${cle}</td>
      <td><input class="cc-set" type="text" size="20" maxlength="60" data-act="ref-f" data-f="libelle" aria-label="${escapeAttr(t("cc_ref_col_libelle"))}" value="${escapeAttr(ed.libelle)}"></td>
      ${isTypes ? `<td><select class="cc-set" data-act="ref-f" data-f="categorie" aria-label="${escapeAttr(t("cc_ref_col_categorie"))}">${cats}${auto}</select></td>` : ""}
      <td><button type="button" class="btn btn-sm cc-act arm" data-act="ref-save">${escapeHtml(t("cc_esc_save"))}</button> <button type="button" class="btn btn-sm cc-act" data-act="ref-cancel">${escapeHtml(t("cc_rights_cancel"))}</button></td></tr>`;
  }
  const lib = e.libelle ? escapeHtml(e.libelle) : `<span class="ref-vide">${escapeHtml(t("cc_ref_cle_affichee"))}</span>`;
  const cat = isTypes ? `<td>${escapeHtml(catLabel(e.categorie))}${e.forcee ? ` <span class="ref-force">${escapeHtml(t("cc_ref_forcee"))}</span>` : ""}</td>` : "";
  const act = admin ? `<td><button type="button" class="btn btn-sm cc-act" data-act="ref-edit" data-liste="${liste}" data-cle="${escapeAttr(e.cle)}">${escapeHtml(t("cc_ref_modifier"))}</button></td>` : "";
  return `<tr data-liste="${liste}"><td>${cle}</td><td>${lib}</td>${cat}${act}</tr>`;
}

function commandRefBloc(liste, admin){
  const isTypes = liste === "types";
  const toutes = COMMAND_REF[liste];
  const rows = toutes.filter(commandRefMatch);
  const titre = escFill(t(isTypes ? "cc_ref_types_title" : "cc_ref_armes_title"), {n: toutes.length});
  const corps = rows.length
    ? `<div class="cc-wrap"><table class="cc-table"><thead><tr><th>${escapeHtml(t("cc_ref_col_cle"))}</th><th>${escapeHtml(t("cc_ref_col_libelle"))}</th>${isTypes ? `<th>${escapeHtml(t("cc_ref_col_categorie"))}</th>` : ""}${admin ? `<th>${escapeHtml(t("cc_camp_col_actions"))}</th>` : ""}</tr></thead><tbody>${rows.map(e => commandRefLigne(liste, e, admin)).join("")}</tbody></table></div>`
    : `<div class="cc-state">${escapeHtml(t("cc_ref_empty_filter"))}</div>`;
  return `<div class="cc-block"><h3 class="cc-sub">${escapeHtml(titre)}</h3>${corps}</div>`;
}

// Les deux tableaux seuls : le filtre et « Modifier » ne touchent jamais la barre (le champ garde le focus).
function renderCommandRefBlocs(){
  const box = $("#cc-ref-blocs");
  if(!box || !COMMAND_REF) return;
  const admin = commandRefIsAdmin();
  box.innerHTML = commandRefBloc("types", admin) + commandRefBloc("armes", admin);
  ccStampLabels(box);
}

function renderCommandRef(){
  const box = $("#cc-ref-fiche");
  if(!box) return;
  if(commandRefLoadState === "loading" || commandRefLoadState === "idle"){
    const rows = ["70%","90%","60%","85%","75%"].map((w,i)=>`<span class="skel" style="width:${w}"></span><span class="skel" style="width:${i%2?"55%":"80%"}"></span>`).join("");
    box.innerHTML = `<div class="cc-fiche">${rows}</div>`;
    renderCommandRefNote();
    return;
  }
  if(commandRefLoadState === "error" || !COMMAND_REF){
    box.innerHTML = `<div class="cc-state"><div>${escapeHtml(t("cc_ref_error"))}</div><div class="cc-state-act"><button type="button" class="btn btn-sm" data-act="ref-retry">${escapeHtml(t("cc_camp_retry"))}</button></div></div>`;
    renderCommandRefNote();
    return;
  }
  const admin = commandRefIsAdmin();
  box.innerHTML = `
    <p class="cc-hint">${escapeHtml(t("cc_ref_hint") + (admin ? " " + t("cc_esc_admin_only") : ""))}</p>
    <div class="cc-row" style="margin:.2rem 0 .4rem">
      <input class="cc-set" type="search" size="24" id="cc-ref-q" data-act="ref-q" placeholder="${escapeAttr(t("cc_ref_search_ph"))}" aria-label="${escapeAttr(t("cc_ref_search_ph"))}" value="${escapeAttr(commandRefFiltre.q)}">
      <button type="button" class="btn btn-sm cc-act${commandRefFiltre.sans ? " arm" : ""}" data-act="ref-sans" aria-pressed="${commandRefFiltre.sans ? "true" : "false"}">${escapeHtml(escFill(t("cc_ref_sans_libelle"), {n: commandRefSansLibelle()}))}</button>
      <span style="flex:1"></span>
      <button type="button" class="btn btn-sm cc-act" data-act="ref-export">${escapeHtml(t("cc_ref_export"))}</button>
      ${admin ? `<button type="button" class="btn btn-sm cc-act" data-act="ref-import">${escapeHtml(t("cc_ref_import"))}</button>
      <input type="file" class="hidden" accept=".json,application/json" data-act="ref-import-pick">` : ""}
    </div>
    <div id="cc-ref-blocs"></div>`;
  renderCommandRefBlocs();
  renderCommandRefNote();
}

function renderCommandRefNote(){
  const zone = $("#cc-ref-note-zone");
  if(!zone) return;
  const n = commandRefNote;
  if(!n){ zone.innerHTML = ""; return; }
  if(n.kind === "msg"){
    const text = n.key ? escFill(t(n.key), n.vars || {}) : n.text;
    zone.innerHTML = `<div class="cc-note${n.deny ? " deny" : ""}">${escapeHtml(text)}</div>`;
    return;
  }
  if(n.kind === "import"){
    const b = n.bilan, refus = b.refuses || [];
    const vars = {
      contrat: b.contrat, version: b.version,
      tp: b.types.poses, ti: b.types.inchanges, tc: b.types.forcees,
      ap: b.armes.poses, ai: b.armes.inchanges, r: refus.length,
    };
    // Le nom du fichier se pose en gras ; tout le reste est échappé.
    const phrase = t("cc_ref_import_bilan").split("{fichier}")
      .map(part => escapeHtml(escFill(part, vars))).join(`<b>${escapeHtml(n.fichier)}</b>`);
    const liste = refus.map(r => "<br>" + escapeHtml(escFill(t("cc_ref_refus_item"), {cle: r.cle, raison: r.raison}))).join("");
    zone.innerHTML = ccConfirmHtml({
      titre: t("cc_ref_import_titre"), texte: phrase + liste, err: n.erreur || null, occupe: !!n.enCours,
      annuler: "ref-import-cancel", ok: "ref-import-apply", libelle: t("cc_rights_confirm_apply"),
    });
  }
}

function commandRefNoteDeny(err){
  commandRefNote = {kind:"msg", deny:true, text: (err && err.message) || t("error_generic")};
  renderCommandRefNote();
}

function commandRefDateCompacte(){
  const d = new Date();
  return String(d.getFullYear()) + String(d.getMonth() + 1).padStart(2, "0") + String(d.getDate()).padStart(2, "0");
}

// L'export est fabriqué ici, depuis la liste affichée : toutes les clés connues, libellé `null`
// compris, `categorie` = la catégorie forcée ou `null` -- un fichier qu'on réimporte tel quel.
function commandRefExporter(){
  if(!COMMAND_REF) return;
  const contenu = {
    contrat: REF_CONTRAT,
    version: 1,
    types: COMMAND_REF.types.map(e => ({cle: e.cle, libelle: e.libelle || null, categorie: e.forcee ? e.categorie : null})),
    armes: COMMAND_REF.armes.map(e => ({cle: e.cle, libelle: e.libelle || null})),
  };
  const blob = new Blob([JSON.stringify(contenu, null, 1) + "\n"], {type: "application/json"});
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = `referentiel_types_armes_${commandRefDateCompacte()}.json`;
  document.body.appendChild(a);
  a.click();
  a.remove();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}

async function commandRefImportPick(input){
  const file = input.files && input.files[0];
  if(!file) return;
  input.value = "";
  const invalide = raison => {
    commandRefNote = {kind:"msg", deny:true, text: escFill(t("cc_ref_import_invalide"), {fichier: file.name, raison})};
    renderCommandRefNote();
  };
  let contenu;
  try {
    contenu = JSON.parse(await file.text());
    if(!contenu || typeof contenu !== "object" || Array.isArray(contenu)) throw new Error("not a JSON object");
  } catch(err){
    return invalide(err.message);
  }
  try {
    const bilan = await apiFetch("/api/command/referentiels/import?appliquer=0", {
      method: "POST",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify(contenu),
    });
    commandRefNote = {kind:"import", fichier: file.name, bilan, contenu};
    renderCommandRefNote();
  } catch(err){
    invalide(typeof err.message === "string" ? err.message : t("error_generic"));
  }
}

async function commandRefEnregistrer(){
  const ed = commandRefEdit;
  if(!ed) return;
  const isTypes = ed.liste === "types";
  const body = isTypes
    ? {cle: ed.cle, libelle: ed.libelle.trim(), categorie: ed.categorie || null}
    : {cle: ed.cle, libelle: ed.libelle.trim()};
  try {
    await apiFetch("/api/command/referentiels/" + ed.liste, {
      method: "PATCH",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify(body),
    });
  } catch(err){
    return commandRefNoteDeny(err); // la ligne reste ouverte, la saisie aussi
  }
  commandRefEdit = null;
  commandRefNote = {kind:"msg", key:"cc_ref_saved", vars:{cle: ed.cle}};
  await reloadCommandRef();
}

function wireCommandRefEvents(){
  const view = $("#view-cc-referentiels");
  if(!view || view.dataset.wired) return; // câblage unique
  view.dataset.wired = "1";

  view.addEventListener("input", e=>{
    const q = e.target.closest('input[data-act="ref-q"]');
    if(q){ commandRefFiltre.q = q.value; renderCommandRefBlocs(); return; }
    const f = e.target.closest('input[data-act="ref-f"]');
    if(f && commandRefEdit) commandRefEdit[f.dataset.f] = f.value;
  });

  view.addEventListener("change", e=>{
    const pick = e.target.closest('input[type="file"][data-act="ref-import-pick"]');
    if(pick){ commandRefImportPick(pick); return; }
    const sel = e.target.closest('select[data-act="ref-f"]');
    if(sel && commandRefEdit) commandRefEdit.categorie = sel.value;
  });

  view.addEventListener("keydown", e=>{
    if(e.key === "Enter" && e.target.closest('input[data-act="ref-f"]')){ e.preventDefault(); commandRefEnregistrer(); }
    if(e.key === "Escape" && commandRefEdit){ commandRefEdit = null; renderCommandRefBlocs(); }
  });

  view.addEventListener("click", e=>{
    const b = e.target.closest("[data-act]");
    if(!b || b.tagName === "INPUT" || b.tagName === "SELECT") return;
    const act = b.dataset.act;

    if(act === "ref-retry"){ loadCommandRef(); return; }
    if(act === "ref-sans"){
      commandRefFiltre.sans = !commandRefFiltre.sans;
      renderCommandRef();
      return;
    }
    if(act === "ref-export"){ commandRefExporter(); return; }
    if(act === "ref-import"){
      const input = view.querySelector('input[data-act="ref-import-pick"]');
      if(input) input.click();
      return;
    }
    if(act === "ref-edit"){
      const liste = b.dataset.liste, cle = b.dataset.cle;
      const e0 = COMMAND_REF[liste].find(x => x.cle === cle);
      if(!e0) return;
      commandRefNote = null;
      renderCommandRefNote();
      // Une seule ligne ouverte à la fois ; « Automatique » est préchoisi tant que la catégorie n'est pas forcée.
      commandRefEdit = {liste, cle, libelle: e0.libelle || "", categorie: liste === "types" && e0.forcee ? e0.categorie : ""};
      renderCommandRefBlocs();
      const champ = view.querySelector('tr.cc-you input[data-f="libelle"]');
      if(champ) champ.focus();
      return;
    }
    if(act === "ref-cancel"){ commandRefEdit = null; renderCommandRefBlocs(); return; }
    if(act === "ref-save"){ commandRefEnregistrer(); return; }
    if(act === "ref-import-cancel"){
      if(commandRefNote && commandRefNote.enCours) return; // addendum 1 : la note est occupée
      commandRefNote = null; renderCommandRefNote(); return;
    }
    if(act === "ref-import-apply"){
      const n = commandRefNote;
      if(!n || n.kind !== "import") return;
      if(n.enCours) return;
      n.erreur = null;
      n.enCours = true;
      ccConfirmOccupe(b);
      (async ()=>{
        try {
          await apiFetch("/api/command/referentiels/import?appliquer=1", {
            method: "POST",
            headers: {"Content-Type": "application/json"},
            body: JSON.stringify(n.contenu),
          });
        } catch(err){
          // Lot « Le Centre au doigt et à la charte » (R5) : la note reste armée et porte le refus du serveur.
          n.enCours = false;
          n.erreur = err.message || t("error_generic");
          if(commandRefNote === n) renderCommandRefNote();
          return;
        }
        n.enCours = false;
        commandRefEdit = null;
        commandRefNote = {kind:"msg", key:"cc_ref_import_done"};
        try { await reloadCommandRef(); } catch(_e){ /* v1.0099 : l'import a réussi ; seule la relecture a échoué, l'écran reste tel quel. */ }
      })();
      return;
    }
  });
}


/* ===================================================================
   Lot « L'écran Archives du Centre » -- Centre de Commandement, l'onglet
   Archives, le septième et dernier : les membres sortis de l'effectif à
   l'appel (un nom ouvre la fiche F au Débrief pour qui y a accès) et, pour
   un administrateur seul, les sauvegardes -- celles du déploiement, les
   manuelles et les automatiques, à télécharger, avec « Sauvegarder maintenant ». La
   restauration ne se fait jamais d'ici (guide, chapitre 11). Patron des états : l'écran
   Escadre. Le balisage est celui de la maquette validée du CdP.
   =================================================================== */
let commandArchLoadState = "idle"; // idle | loading | ready | error
let COMMAND_ARCH = null;           // {you:{is_admin}, membres:[…], sauvegardes:[…] | null, automatique:{intervalle_h, garder, echec} | null}
let commandArchNote = null;        // null | {kind:"busy"} | {kind:"done", base, ecussons} | {kind:"deny", text}

function fmtOctets(n){
  const loc = currentLang === "fr" ? "fr-FR" : "en-GB";
  if(n >= 1048576) return (n/1048576).toLocaleString(loc, {maximumFractionDigits:1}) + (currentLang === "fr" ? " Mo" : " MB");
  return Math.max(1, Math.round(n/1024)).toLocaleString(loc) + (currentLang === "fr" ? " Ko" : " KB");
}

function commandArchMembreRowHtml(m){
  const peutF = ME && (ME.capabilities||[]).includes("debrief.access");
  const nom = escapeHtml(callsign(m.name));
  const lien = peutF ? `<a href="#" data-arch-membre="${escapeAttr(m.id)}">${nom}</a>` : nom;
  return `<tr>
    <td><span class="mbr-name"><span class="avatar">${avatarHtml(m.id, m.avatar_hash, m.name)}</span>${lien}</span></td>
    <td class="mbr-rank">${escapeHtml(m.escadrille || "—")}</td>
    <td class="mbr-seen">${escapeHtml(fmtLocalDate(m.archived_at))}</td>
    <td class="mbr-seen">${m.missions}</td>
    <td class="mbr-seen">${escapeHtml(fmtHeures(m.heures))}</td>
  </tr>`;
}

function commandArchSauvRowHtml(s){
  const dl = (fichier, cle) => `<a class="btn btn-sm cc-act" href="/api/command/archives/sauvegardes/${escapeAttr(fichier)}" download>${escapeHtml(t(cle))}</a>`;
  const total = s.base_octets + (s.ecussons_octets || 0);
  return `<tr>
    <td class="mbr-seen">${escapeHtml(fmtLocalDate(s.date))} · ${escapeHtml(fmtLocalTime(s.date))}</td>
    <td><span class="cc-office${s.origine === "manuelle" ? " porte" : ""}">${escapeHtml(t(s.origine === "manuelle" ? "cc_arch_origine_manuelle" : s.origine === "automatique" ? "cc_arch_origine_automatique" : s.origine === "migration" ? "cc_arch_origine_migration" : "cc_arch_origine_deploiement"))}</span></td>
    <td class="mbr-seen">${escapeHtml(s.revision)}</td>
    <td class="mbr-seen">${escapeHtml(fmtOctets(total))}</td>
    <td><span class="cc-row">${dl(s.fichier_base, "cc_arch_dl_base")}${s.fichier_ecussons ? dl(s.fichier_ecussons, "cc_arch_dl_ecussons") : ""}</span></td>
  </tr>`;
}

// Lot « Les sauvegardes automatiques » : le panneau de réglage, juste après la note du bouton. Deux
// listes (fréquence, rétention) et l'état : l'échec de la dernière tentative, sinon la dernière
// automatique de la liste, sinon « aucune ». Les valeurs permises sont celles du serveur
// (sauvegardes_auto.FREQUENCES_H / RETENTIONS).
function commandArchAutoHtml(d){
  const a = d.automatique;
  if(!a) return "";
  const option = (valeur, libelle, choisi) =>
    `<option value="${valeur}"${choisi === valeur ? " selected" : ""}>${escapeHtml(libelle)}</option>`;
  const freq = [0, 6, 12, 24, 48, 168].map(h => option(h,
    h === 0 ? t("cc_arch_auto_freq_0") : h === 168 ? t("cc_arch_auto_freq_168") : escFill(t("cc_arch_auto_freq_h"), {n: h}),
    a.intervalle_h)).join("");
  const garder = [3, 7, 14, 30].map(n => option(n, escFill(t("cc_arch_auto_garder"), {n}), a.garder)).join("");
  let etat;
  if(a.echec){
    etat = escFill(t("cc_arch_auto_echec"), {date: fmtLocalDate(a.echec.date), heure: fmtLocalTime(a.echec.date), raison: a.echec.raison});
  } else {
    const derniere = (d.sauvegardes || []).find(s => s.origine === "automatique");
    etat = derniere
      ? escFill(t("cc_arch_auto_derniere"), {date: fmtLocalDate(derniere.date), heure: fmtLocalTime(derniere.date)})
      : t("cc_arch_auto_aucune");
  }
  return `<div class="cc-note${a.echec ? " deny" : ""}">
      <span>${escapeHtml(t("cc_arch_auto_title"))}</span>
      <select class="cc-set" data-act="arch-auto" data-f="intervalle_h" aria-label="${escapeAttr(t("cc_arch_auto_aria_freq"))}">${freq}</select>
      <select class="cc-set" data-act="arch-auto" data-f="garder" aria-label="${escapeAttr(t("cc_arch_auto_aria_garder"))}">${garder}</select>
      <span>${escapeHtml(etat)}</span>
    </div>`;
}

// Lot « La réception du .rrlog de l'agent » (v1.0089) : le bloc « Serveur DCS » de l'écran Archives, pour un
// administrateur seul -- le jeton de l'agent du serveur DCS (émettre, remplacer, révoquer) et les vingt derniers
// fichiers reçus. Le jeton en clair ne vit que dans `commandAgentJeton`, rempli par la réponse de l'émission et
// effacé au prochain chargement de l'écran Archives : jamais dans `localStorage`, une URL ou le DOM d'un autre écran.
let commandAgentEtat = "idle";   // idle | loading | ready | error
let COMMAND_AGENT = null;        // {jeton:{emis_le, emis_par:{id, nom}, dernier_envoi_le} | null, recus:[…]}
let commandAgentConf = null;     // null | {kind:"remplacer"|"revoquer", occupe}
let commandAgentErr = null;      // le refus du serveur (texte), écrit en .cc-note.deny
let commandAgentOccupe = false;  // un appel est en cours : les boutons sont occupés
let commandAgentJeton = null;    // null | {jeton, adresse} -- le panneau de l'émission

function commandAgentChampHtml(cle, libelle, valeur){
  return `<div class="cc-row cc-agent-champ"><span class="cc-office">${escapeHtml(libelle)}</span>` +
    `<input class="cc-set" type="text" readonly size="48" value="${escapeAttr(valeur)}" aria-label="${escapeAttr(libelle)}" data-agent-champ="${cle}">` +
    `<button type="button" class="btn btn-sm cc-act" data-act="agent-copy" data-champ="${cle}">${escapeHtml(t("cc_lien_copy"))}</button></div>`;
}

function commandAgentRecuHtml(x){
  return `<tr><td class="mbr-seen">${escapeHtml(fmtLocalDate(x.recu_le))} · ${escapeHtml(fmtLocalTime(x.recu_le))}</td>
    <td class="sqn-full">${escapeHtml(x.mission || "—")}</td><td class="mbr-rank">${escapeHtml(x.theatre || "—")}</td>
    <td class="mbr-seen">${escapeHtml(x.date_mission || "—")}</td><td class="mbr-seen">${escapeHtml(fmtOctets(x.taille))}</td>
    <td><span class="cc-office">${escapeHtml(x.etat === "en_attente" ? t("cc_agent_etat_attente") : x.etat)}</span></td></tr>`;
}

function commandAgentHtml(){
  const entete = `<h3 class="cc-sub">${escapeHtml(t("cc_agent_title"))}</h3><p class="cc-hint">${escapeHtml(t("cc_agent_hint"))}</p>`;
  let corps;
  if(commandAgentEtat === "error"){
    corps = `<div class="cc-state"><div>${escapeHtml(t("cc_arch_error"))}</div><div class="cc-state-act"><button type="button" class="btn btn-sm" data-act="agent-retry">${escapeHtml(t("cc_camp_retry"))}</button></div></div>`;
  } else if(!COMMAND_AGENT){
    corps = `<div class="cc-fiche"><span class="skel" style="width:80%"></span><span class="skel" style="width:60%"></span></div>`;
  } else {
    const j = COMMAND_AGENT.jeton;
    const dis = commandAgentOccupe ? " disabled" : "";
    const boutons = `<div class="cc-row"><button type="button" class="btn btn-sm cc-act" data-act="${j ? "agent-remplacer" : "agent-emettre"}"${dis}>${escapeHtml(t(j ? "cc_agent_remplacer" : "cc_agent_emettre"))}</button>` +
      (j ? `<button type="button" class="btn btn-sm cc-act" data-act="agent-revoquer"${dis}>${escapeHtml(t("cc_agent_revoquer"))}</button>` : "") + `</div>`;
    const envoi = j && j.dernier_envoi_le
      ? escFill(t("cc_agent_envoi_le"), {date: fmtLocalDate(j.dernier_envoi_le), heure: fmtLocalTime(j.dernier_envoi_le)})
      : t("cc_agent_envoi_aucun");
    const etat = j
      ? `<div class="cc-note"><span>${escapeHtml(escFill(t("cc_agent_actif"), {date: fmtLocalDate(j.emis_le), nom: callsign(j.emis_par.nom), envoi}))}</span></div>`
      : `<div class="cc-note deny"><span>${escapeHtml(t("cc_agent_aucun"))}</span></div>`;
    const refus = commandAgentErr ? `<div class="cc-note deny"><span>${escapeHtml(commandAgentErr)}</span></div>` : "";
    const c = commandAgentConf;
    const confirm = c ? ccConfirmHtml({
      titre: t(c.kind === "revoquer" ? "cc_agent_conf_revoquer_titre" : "cc_agent_conf_remplacer_titre"),
      texte: escapeHtml(t("cc_agent_conf_texte")), danger: true,
      annuler: "agent-conf-annuler", ok: "agent-conf-ok",
      libelle: t(c.kind === "revoquer" ? "cc_agent_conf_revoquer_ok" : "cc_agent_conf_remplacer_ok"), occupe: !!c.occupe,
    }) : "";
    const emis = commandAgentJeton
      ? `<div class="cc-note">${commandAgentChampHtml("jeton", t("cc_agent_jeton"), commandAgentJeton.jeton)}${commandAgentChampHtml("adresse", t("cc_agent_adresse"), commandAgentJeton.adresse)}<span>${escapeHtml(t("cc_agent_une_fois"))}</span></div>`
      : "";
    const r = COMMAND_AGENT.recus || [];
    const liste = r.length
      ? `<div class="cc-wrap"><table class="cc-table"><thead><tr>
          <th>${escapeHtml(t("cc_agent_col_recu"))}</th><th>${escapeHtml(t("cc_agent_col_mission"))}</th><th>${escapeHtml(t("cc_agent_col_theatre"))}</th>
          <th>${escapeHtml(t("cc_agent_col_date"))}</th><th>${escapeHtml(t("cc_agent_col_taille"))}</th><th>${escapeHtml(t("cc_agent_col_etat"))}</th></tr></thead>
          <tbody>${r.map(commandAgentRecuHtml).join("")}</tbody></table></div>`
      : `<div class="cc-state">${escapeHtml(t("cc_agent_vide"))}</div>`;
    corps = `${boutons}${etat}${refus}${confirm}${emis}<h3 class="cc-sub cc-agent-recus">${escapeHtml(t("cc_agent_recus"))}</h3>${liste}`;
  }
  return `<div class="cc-block" id="cc-arch-agent">${entete}${corps}</div>`;
}

async function loadCommandAgent(){
  commandAgentEtat = "loading";
  renderCommandArchives();
  try {
    COMMAND_AGENT = await apiFetch("/api/command/agent");
    commandAgentEtat = "ready";
  } catch(e){
    commandAgentEtat = "error";
  }
  renderCommandArchives();
}

// Émettre (sans confirmation) ou, après la confirmation, remplacer : `POST /command/agent/jeton`. La réponse
// porte le jeton, que le panneau montre ; l'état et le journal se relisent. Un refus s'écrit en `.cc-note.deny`.
async function commandAgentEmettre(){
  if(commandAgentOccupe) return;
  commandAgentOccupe = true;
  commandAgentErr = null;
  if(!commandAgentConf) renderCommandArchives();
  let rep;
  try {
    rep = await apiFetch("/api/command/agent/jeton", {method:"POST"});
  } catch(err){
    commandAgentOccupe = false;
    commandAgentConf = null;
    commandAgentErr = (err && err.message) || t("error_generic");
    renderCommandArchives();
    return;
  }
  commandAgentOccupe = false;
  commandAgentConf = null;
  commandAgentJeton = {jeton: rep.jeton, adresse: location.origin + "/api/agent/rrlog"};
  try { COMMAND_AGENT = await apiFetch("/api/command/agent"); } catch(e){ /* l'état se relira au prochain chargement */ }
  renderCommandArchives();
  loadCommandJournal(false);   // l'émission s'y consigne
}

async function commandAgentRevoquer(){
  if(commandAgentOccupe) return;
  commandAgentOccupe = true;
  commandAgentErr = null;
  try {
    await apiFetch("/api/command/agent/jeton", {method:"DELETE"});
  } catch(err){
    commandAgentOccupe = false;
    commandAgentConf = null;
    commandAgentErr = (err && err.message) || t("error_generic");
    renderCommandArchives();
    return;
  }
  commandAgentOccupe = false;
  commandAgentConf = null;
  commandAgentJeton = null;
  try { COMMAND_AGENT = await apiFetch("/api/command/agent"); } catch(e){ /* idem */ }
  renderCommandArchives();
  loadCommandJournal(false);   // la révocation s'y consigne
}

// Copie d'une valeur du panneau : presse-papiers, repli par sélection du champ (comme `copierLienSecours`).
async function copierAgent(cle){
  const valeur = commandAgentJeton && commandAgentJeton[cle];
  const champ = document.querySelector(`#cc-arch-agent input[data-agent-champ="${cle}"]`);
  if(!valeur || !champ) return;
  let copie = false;
  try {
    await navigator.clipboard.writeText(valeur);
    copie = true;
  } catch(e){
    try {
      champ.focus();
      champ.select();
      champ.setSelectionRange(0, valeur.length);
      copie = document.execCommand("copy");
    } catch(e2){ /* le champ reste sélectionné : copie à la main */ }
  }
  if(copie) showToast(t("cc_agent_copie"));
}

function commandAgentClic(b){
  const act = b.dataset.act;
  if(act === "agent-retry"){ loadCommandAgent(); return; }
  if(act === "agent-copy"){ copierAgent(b.dataset.champ); return; }
  if(commandAgentOccupe) return;
  if(act === "agent-emettre"){ commandAgentEmettre(); return; }
  if(act === "agent-remplacer" || act === "agent-revoquer"){
    commandAgentErr = null;
    commandAgentConf = {kind: act === "agent-revoquer" ? "revoquer" : "remplacer", occupe: false};
    renderCommandArchives();
    return;
  }
  if(act === "agent-conf-annuler"){ commandAgentConf = null; renderCommandArchives(); return; }
  if(act === "agent-conf-ok" && commandAgentConf){
    commandAgentConf.occupe = true;
    ccConfirmOccupe(b);
    if(commandAgentConf.kind === "revoquer") commandAgentRevoquer(); else commandAgentEmettre();
  }
}

function renderCommandArchives(){
  const box = $("#cc-arch-fiche");
  if(!box) return;
  if(commandArchLoadState === "loading" || commandArchLoadState === "idle"){
    const rows = ["70%","90%","60%","85%","75%"].map((w,i)=>`<span class="skel" style="width:${w}"></span><span class="skel" style="width:${i%2?"55%":"80%"}"></span>`).join("");
    box.innerHTML = `<div class="cc-fiche">${rows}</div>`;
    return;
  }
  if(commandArchLoadState === "error" || !COMMAND_ARCH){
    box.innerHTML = `<div class="cc-state"><div>${escapeHtml(t("cc_arch_error"))}</div><div class="cc-state-act"><button type="button" class="btn btn-sm" data-act="arch-retry">${escapeHtml(t("cc_camp_retry"))}</button></div></div>`;
    return;
  }
  const d = COMMAND_ARCH;
  const membres = d.membres.length
    ? `<div class="cc-wrap"><table class="cc-table"><thead><tr>
        <th>${escapeHtml(t("cc_arch_col_membre"))}</th><th>${escapeHtml(t("cc_arch_col_escadrille"))}</th>
        <th>${escapeHtml(t("cc_arch_col_sortie"))}</th><th>${escapeHtml(t("cc_arch_col_missions"))}</th>
        <th>${escapeHtml(t("cc_arch_col_heures"))}</th></tr></thead>
        <tbody>${d.membres.map(commandArchMembreRowHtml).join("")}</tbody></table></div>`
    : `<div class="cc-state">${escapeHtml(t("cc_arch_mbr_empty"))}</div>`;
  let sauv = "";
  if(d.you.is_admin){
    const n = commandArchNote;
    const note = !n ? "" : n.kind === "busy"
      ? `<div class="cc-note">${escapeHtml(t("cc_arch_sav_busy"))}</div>`
      : n.kind === "deny"
      ? `<div class="cc-note deny">${escapeHtml(n.text)}</div>`
      : `<div class="cc-note">${escapeHtml(escFill(t("cc_arch_sav_done"), {taille: fmtOctets(n.base + n.ecussons)}))}</div>`;
    sauv = `<div class="cc-block"><h3 class="cc-sub">${escapeHtml(t("cc_arch_sav_title"))}</h3>
      <p class="cc-hint">${escapeHtml(t("cc_arch_sav_hint"))}</p>
      <div class="cc-row"><button type="button" class="btn btn-sm cc-act" data-act="arch-save"${n && n.kind === "busy" ? " disabled" : ""}>${escapeHtml(t("cc_arch_sav_btn"))}</button></div>
      ${note}
      ${commandArchAutoHtml(d)}
      ${d.sauvegardes.length ? `<div class="cc-wrap"><table class="cc-table"><thead><tr>
        <th>${escapeHtml(t("cc_arch_col_date"))}</th><th>${escapeHtml(t("cc_arch_col_origine"))}</th>
        <th>${escapeHtml(t("cc_arch_col_revision"))}</th><th>${escapeHtml(t("cc_arch_col_taille"))}</th>
        <th>${escapeHtml(t("cc_arch_col_fichiers"))}</th></tr></thead>
        <tbody>${d.sauvegardes.map(commandArchSauvRowHtml).join("")}</tbody></table></div>`
        : `<div class="cc-state">${escapeHtml(t("cc_arch_sav_empty"))}</div>`}</div>`;
  }
  const journal = d.you.is_admin ? commandJrHtml() : "";
  const agent = d.you.is_admin ? commandAgentHtml() : "";   // Lot « La réception du .rrlog de l'agent »
  box.innerHTML = `<h3 class="cc-sub">${escapeHtml(t("cc_arch_mbr_title"))}</h3>
    <p class="cc-hint">${escapeHtml(t("cc_arch_mbr_hint"))}</p>
    ${membres}
    ${sauv}
    ${agent}
    ${journal}`;
  ccStampLabels(box);
}

/* Lot « Polish du Centre » : le journal des modifications, à l'écran Archives, pour un administrateur
   seul. Chaque écriture du Centre s'y consigne (qui, quand, quoi, l'avant et l'après) ; le serveur rend
   les entrées les plus récentes d'abord, cinquante par page (GET /command/journal), les comptes déjà
   nommés ; l'écran nomme les rôles (ccRoleName). */
let commandJrState = "idle";   // idle | loading | ready | error
let COMMAND_JR = [];           // les entrées lues, les plus récentes d'abord
let commandJrSuite = false;    // d'autres, plus anciennes, restent à lire

function commandJrValeur(champ, v, objet){
  if(v == null || v === "") return "—";
  // Lot « La page Configuration du Centre » : la valeur d'un secret n'est jamais journalisée, seulement son état.
  if(champ === "valeur" && CFG_SECRETS.includes(objet)){
    const k = {"rempli": "cc_cfg_s_rempli", "vide": "cc_cfg_s_vide", "remplacé": "cc_cfg_s_remplace"}[v];
    if(k) return t(k);
  }
  if(/role_ids?$/.test(champ)) return ccRoleName(v);
  // Lot « La plume » §6 : la catégorie forcée d'un type, dans la langue de l'écran.
  if(champ === "categorie") return catLabel(String(v));
  return String(v);
}

function commandJrLigneHtml(l, objet){
  // Lot « L'accès invité » : le champ `jusqua` des invitations réemploie la colonne « Jusqu'au ».
  const lib = escapeHtml(t(l.champ === "jusqua" ? "cc_inv_col_jusqua" : "cc_jr_f_" + l.champ));
  if(l.ajoutes || l.retires){
    const plus = (l.ajoutes || []).map(v => "+ " + escapeHtml(commandJrValeur(l.champ, v, objet)));
    const moins = (l.retires || []).map(v => "− " + escapeHtml(commandJrValeur(l.champ, v, objet)));
    return `${lib} : ${plus.concat(moins).join(" · ")}`;
  }
  if(l.avant == null) return `${lib} : ${escapeHtml(commandJrValeur(l.champ, l.apres, objet))}`;
  return `${lib} : ${escapeHtml(commandJrValeur(l.champ, l.avant, objet))} → ${escapeHtml(commandJrValeur(l.champ, l.apres, objet))}`;
}

// Lot « La page Configuration du Centre » : la colonne Objet d'un réglage montre son libellé ; celle d'un compte nommé ou retiré, son nom.
function commandJrObjet(e){
  if(e.action === "reglage.edit") return Object.prototype.hasOwnProperty.call(I18N[currentLang], "cc_cfg_l_" + e.objet) ? t("cc_cfg_l_" + e.objet) : (e.objet || "—");
  if(e.action === "admin.nommer" || e.action === "admin.retirer") return e.objet ? commandCfgNom(e.objet) : "—";
  return e.objet || "—";
}

function commandJrRowHtml(e){
  return `<tr>
    <td class="mbr-seen">${escapeHtml(fmtLocalDate(e.fait_le))} · ${escapeHtml(fmtLocalTime(e.fait_le))}</td>
    <td>${escapeHtml(callsign(e.par.nom))}</td>
    <td><span class="cc-office porte">${escapeHtml(t("cc_jr_a_" + e.action.replace(/\./g, "_")))}</span></td>
    <td class="sqn-full">${escapeHtml(commandJrObjet(e))}</td>
    <td class="sqn-full">${e.lignes.length ? e.lignes.map(l => commandJrLigneHtml(l, e.objet)).join("<br>") : "—"}</td>
  </tr>`;
}

function commandJrHtml(){
  let corps;
  if(commandJrState === "error"){
    corps = `<div class="cc-state"><div>${escapeHtml(t("cc_jr_error"))}</div><div class="cc-state-act"><button type="button" class="btn btn-sm" data-act="jr-retry">${escapeHtml(t("cc_camp_retry"))}</button></div></div>`;
  } else if(!COMMAND_JR.length && commandJrState !== "ready"){
    corps = `<div class="cc-fiche"><span class="skel" style="width:80%"></span><span class="skel" style="width:60%"></span></div>`;
  } else if(!COMMAND_JR.length){
    corps = `<div class="cc-state">${escapeHtml(t("cc_jr_empty"))}</div>`;
  } else {
    corps = `<div class="cc-wrap"><table class="cc-table"><thead><tr>
        <th>${escapeHtml(t("cc_jr_col_date"))}</th><th>${escapeHtml(t("cc_jr_col_par"))}</th><th>${escapeHtml(t("cc_jr_col_action"))}</th>
        <th>${escapeHtml(t("cc_jr_col_objet"))}</th><th>${escapeHtml(t("cc_jr_col_detail"))}</th></tr></thead>
        <tbody>${COMMAND_JR.map(commandJrRowHtml).join("")}</tbody></table></div>`
      + (commandJrSuite ? `<div class="cc-row"><button type="button" class="btn btn-sm" data-act="jr-more"${commandJrState === "loading" ? " disabled" : ""}>${escapeHtml(t("cc_jr_more"))}</button></div>` : "");
  }
  return `<div class="cc-block" id="cc-arch-journal"><h3 class="cc-sub">${escapeHtml(t("cc_jr_title"))}</h3>
    <p class="cc-hint">${escapeHtml(t("cc_jr_hint"))}</p>
    ${corps}</div>`;
}

async function loadCommandJournal(plus){
  if(commandJrState === "loading") return;
  commandJrState = "loading";
  if(!plus){ COMMAND_JR = []; commandJrSuite = false; }
  renderCommandArchives();
  try {
    await ensureCommandDiscordRolesLoaded();
    const avant = plus && COMMAND_JR.length ? `?avant=${COMMAND_JR[COMMAND_JR.length - 1].id}` : "";
    const d = await apiFetch("/api/command/journal" + avant);
    COMMAND_JR = COMMAND_JR.concat(d.entrees || []);
    commandJrSuite = !!d.suite;
    commandJrState = "ready";
  } catch(e){
    commandJrState = "error";
  }
  renderCommandArchives();
}

async function loadCommandArchives(){
  commandArchLoadState = "loading";
  // Lot « La réception du .rrlog de l'agent » : le jeton en clair s'efface au chargement de l'écran.
  commandAgentJeton = null; commandAgentConf = null; commandAgentErr = null; commandAgentOccupe = false;
  renderCommandArchives();
  try {
    COMMAND_ARCH = await apiFetch("/api/command/archives");
    commandArchLoadState = "ready";
  } catch(e){
    commandArchLoadState = "error";
  }
  renderCommandArchives();
  if(commandArchLoadState === "ready" && COMMAND_ARCH.you.is_admin){
    loadCommandJournal(false);
    loadCommandAgent();   // Lot « La réception du .rrlog de l'agent »
  }
}

function ensureCommandArchivesLoaded(){
  // Lot « La réception du .rrlog de l'agent » : revenir à l'écran Archives efface aussi le jeton en clair.
  commandAgentJeton = null;
  if(commandArchLoadState === "ready" || commandArchLoadState === "loading"){
    renderCommandArchives();
  } else {
    loadCommandArchives();
  }
}

// « Sauvegarder maintenant » : le bouton est désactivé pendant la sauvegarde ;
// à la réussite la liste se relit (la neuve en tête) ; à l'échec (409, 500) le
// `detail` du serveur s'écrit en `.cc-note.deny` et rien n'a été gardé.
async function commandArchSauvegarder(){
  if(commandArchNote && commandArchNote.kind === "busy") return;
  commandArchNote = {kind:"busy"};
  renderCommandArchives();
  let entree;
  try {
    entree = await apiFetch("/api/command/archives/sauvegarde", {method:"POST"});
  } catch(err){
    commandArchNote = {kind:"deny", text: (err && err.message) || t("error_generic")};
    renderCommandArchives();
    return;
  }
  try {
    COMMAND_ARCH = await apiFetch("/api/command/archives");
  } catch(e){
    // Relecture impossible : la sauvegarde existe, l'entrée rendue se pose en tête.
    COMMAND_ARCH.sauvegardes = [entree].concat(COMMAND_ARCH.sauvegardes || []);
  }
  commandArchNote = {kind:"done", base: entree.base_octets, ecussons: entree.ecussons_octets || 0};
  renderCommandArchives();
  loadCommandJournal(false);   // la sauvegarde s'y consigne
}

// Lot « Les sauvegardes automatiques » : un changement de l'une des deux listes envoie les deux valeurs
// (PUT), listes désactivées le temps de la requête. À la réussite, le réglage rendu remplace l'ancien et
// le journal se relit ; à l'échec, la note de refus s'écrit et les listes reviennent au réglage enregistré.
async function commandArchAutoRegler(view){
  const listes = view.querySelectorAll('[data-act="arch-auto"]');
  const freq = view.querySelector('[data-act="arch-auto"][data-f="intervalle_h"]');
  const garder = view.querySelector('[data-act="arch-auto"][data-f="garder"]');
  if(!freq || !garder) return;
  const corps = {intervalle_h: Number(freq.value), garder: Number(garder.value)};
  listes.forEach(l => { l.disabled = true; });
  try {
    COMMAND_ARCH.automatique = await apiFetch("/api/command/archives/automatique", {
      method: "PUT", headers: {"Content-Type": "application/json"}, body: JSON.stringify(corps)
    });
  } catch(err){
    commandArchNote = {kind:"deny", text: (err && err.message) || t("error_generic")};
    renderCommandArchives();
    return;
  }
  if(commandArchNote && commandArchNote.kind === "deny") commandArchNote = null;
  renderCommandArchives();
  loadCommandJournal(false);   // le réglage s'y consigne
}

function wireCommandArchivesEvents(){
  const view = $("#view-cc-archives");
  if(!view || view.dataset.wired) return; // câblage unique
  view.dataset.wired = "1";
  view.addEventListener("change", e=>{
    if(e.target.closest('[data-act="arch-auto"]')) commandArchAutoRegler(view);
  });
  view.addEventListener("click", e=>{
    const m = e.target.closest("[data-arch-membre]");
    if(m){
      e.preventDefault();
      $("#screen-app").dataset.module = "debrief";
      goDebrief("membre", {memberId: m.dataset.archMembre, reset:true});
      return;
    }
    const b = e.target.closest("[data-act]");
    if(!b) return;
    if(b.dataset.act.startsWith("agent-")){ commandAgentClic(b); return; }
    if(b.dataset.act === "arch-retry"){ loadCommandArchives(); return; }
    if(b.dataset.act === "jr-more"){ loadCommandJournal(true); return; }
    if(b.dataset.act === "jr-retry"){ loadCommandJournal(false); return; }
    if(b.dataset.act === "arch-save") commandArchSauvegarder();
  });
}


/* ===================================================================
   Lot « La page Configuration du Centre » (v1.0106, rr-centre-reglages) — le huitième onglet du Centre, réservé aux
   administrateurs : les administrateurs en tête (les fondateurs en lecture, les nommés avec « Retirer », un membre
   choisi pour en nommer un), puis les réglages du serveur, chacun enregistré seul. Les routes sont celles du lot
   v1.0105 (`GET /reglages`, `PUT /reglages/{cle}`, `GET|PUT|DELETE /administrateurs`). Un secret ne dit que « Renseigné »
   ou « Vide » : sa valeur ne se lit jamais, et ce qu'on tape n'est gardé dans aucune variable ni aucun attribut.
   Lot « Le modèle et l'effort du Récit » (v1.0108, rr-centre-config-modele-effort) : le modèle se choisit dans la liste
   des modèles actifs d'Anthropic (`GET /reglages/modeles`), l'effort de rédaction est un réglage de plus, et chaque
   réglage en clair modifié porte « Enregistrer » et « Annuler ».
   Lot « Les dossiers du serveur » (v1.0124, rr-centre-config-montages) : un troisième bloc, en lecture seule, montre les trois
   dossiers que Docker branche au démarrage (`GET /reglages/dossiers`) : présent ou non, et le nombre de fichiers.
   =================================================================== */
const CFG_GROUPES = {fuseau:"cc_cfg_g_fuseau", recit:"cc_cfg_g_recit", digest:"cc_cfg_g_digest", reponses:"cc_cfg_g_reponses", tuiles:"cc_cfg_g_tuiles", suites:"cc_cfg_g_suites"};
const CFG_SECRETS = ["ANTHROPIC_API_KEY", "DISCORD_WEBHOOK_URL", "DISCORD_DIGEST_TOKEN", "DISCORD_BOT_TOKEN"];
let commandCfgLoadState = "idle"; // idle | loading | ready | error
let COMMAND_CFG = null;           // {cle_presente, reglages:[élément…]} -- GET /api/command/reglages
let COMMAND_CFG_ADM = null;       // {fondateurs:[{id, nom}], nommes:[{id, nom, nomme_le, nomme_par}]} -- GET /api/command/administrateurs
let commandCfgChamps = {};        // clé -> le texte tapé d'un réglage EN CLAIR (jamais un secret)
let commandCfgSecret = null;      // la clé du secret dont le champ est ouvert (le champ lui-même ne se garde pas)
let commandCfgOccupe = new Set(); // les clés dont l'envoi court
let commandCfgNote = null;        // la seule note armée de la page : {kind:"nommer"|"retirer", id} | {kind:"vider", cle}, + err, occupe
let commandCfgChoix = "";         // le membre choisi dans le sélecteur « Nommer »
let COMMAND_CFG_MODELES = null;   // {disponible, raison, modeles:[{id, nom, efforts}]} -- GET /api/command/reglages/modeles
let COMMAND_CFG_DOSSIERS = null;  // [{id, variable, chemin, present, fichiers, plafond}] ou null -- GET /api/command/reglages/dossiers
const CFG_MODELES_ERREUR = {disponible: false, raison: "erreur", modeles: []};

// Le nom d'un compte (règle 7) : le membre du Centre, sinon le nom rendu par /administrateurs, sinon « Compte {id} ».
function commandCfgNom(id){
  const sid = String(id);
  const m = (COMMAND_MEMBERS || []).find(x => String(x.id) === sid);
  if(m && m.name) return callsign(m.name);
  const a = COMMAND_CFG_ADM ? COMMAND_CFG_ADM.fondateurs.concat(COMMAND_CFG_ADM.nommes).find(x => String(x.id) === sid) : null;
  if(a && a.nom) return callsign(a.nom);
  return escFill(t("cc_cfg_adm_inconnu"), {id: sid});
}

// Le refus du serveur : son `detail` quand c'est un texte, sinon le message commun.
function commandCfgMessage(e){
  return (e && typeof e.detail === "string" && e.detail) ? e.message : t("error_generic");
}

function commandCfgElement(cle){
  return COMMAND_CFG ? COMMAND_CFG.reglages.find(e => e.cle === cle) : null;
}

function commandCfgTexte(e){
  if(e.type === "booleen") return e.valeur ? "true" : "false";
  return e.valeur == null ? "" : String(e.valeur);
}

function commandCfgDefautHtml(e){
  const d = e.defaut;
  if(d == null || d === "") return escapeHtml(t("cc_cfg_defaut_aucun"));
  let v = String(d);
  if(e.cle === "ANTHROPIC_EFFORT") v = t("cc_cfg_effort_" + d);
  else if(e.type === "choix") v = t("cc_cfg_lang_" + d);
  else if(e.type === "booleen") v = t(d ? "cc_cfg_oui" : "cc_cfg_non");
  return escapeHtml(escFill(t("cc_cfg_defaut_val"), {v}));
}

// Lot « Le modèle et l'effort du Récit » : la liste des modèles quand Anthropic l'a rendue, sinon `null`.
function commandCfgListe(){
  return COMMAND_CFG_MODELES && COMMAND_CFG_MODELES.disponible ? COMMAND_CFG_MODELES.modeles : null;
}

// Les efforts de la liste : ceux du modèle ENREGISTRÉ s'il est dans la liste, sinon les cinq du réglage ; l'effort enregistré
// y est toujours, à sa place dans l'ordre `low … max`.
function commandCfgEffortsOfferts(){
  const eff = commandCfgElement("ANTHROPIC_EFFORT"), mod = commandCfgElement("ANTHROPIC_MODEL"), liste = commandCfgListe();
  const m = liste && mod ? liste.find(x => x.id === commandCfgTexte(mod)) : null;
  const ordre = eff && eff.choix ? eff.choix : ["low", "medium", "high", "xhigh", "max"];
  const offerts = new Set(m ? m.efforts : ordre);
  if(eff) offerts.add(commandCfgTexte(eff));
  return ordre.filter(c => offerts.has(c));
}

// Les options des deux listes (valeur, texte), sans balise.
function commandCfgOptions(e){
  if(e.cle === "ANTHROPIC_EFFORT") return commandCfgEffortsOfferts().map(c => ({v: c, txt: t("cc_cfg_effort_" + c)}));
  const sauve = commandCfgTexte(e), liste = commandCfgListe() || [];
  const opts = liste.map(m => ({v: m.id, txt: m.nom + " (" + m.id + ")"}));
  if(sauve === "") opts.unshift({v: "", txt: t("cc_cfg_modele_choisir")});
  else if(!liste.some(m => m.id === sauve)) opts.unshift({v: sauve, txt: sauve + " " + t("cc_cfg_modele_hors_liste")});
  return opts;
}

// Le champ d'un réglage en clair, prérempli de sa valeur (ou de ce qui a été tapé).
function commandCfgChampHtml(e, occupe){
  let brut = Object.prototype.hasOwnProperty.call(commandCfgChamps, e.cle) ? commandCfgChamps[e.cle] : commandCfgTexte(e);
  const attrs = `class="cc-set" data-act="cfg-champ" data-cle="${escapeAttr(e.cle)}" aria-label="${escapeAttr(t("cc_cfg_l_" + e.cle))}"${occupe ? " disabled" : ""}`;
  if(e.cle === "ANTHROPIC_EFFORT" || (e.cle === "ANTHROPIC_MODEL" && commandCfgListe())){
    const opts = commandCfgOptions(e);
    // Une saisie que la liste n'offre plus (l'autre ligne vient d'être enregistrée, ou la liste vient de changer) est oubliée.
    if(!opts.some(o => o.v === brut)){ delete commandCfgChamps[e.cle]; brut = commandCfgTexte(e); }
    return `<select ${attrs}>${opts.map(o => `<option value="${escapeAttr(o.v)}"${o.v === brut ? " selected" : ""}>${escapeHtml(o.txt)}</option>`).join("")}</select>`;
  }
  if(e.type === "entier"){
    const b = e.bornes || [];
    return `<input type="number" ${attrs} min="${escapeAttr(b[0])}" max="${escapeAttr(b[1])}" step="1" value="${escapeAttr(brut)}">`;
  }
  if(e.type === "choix"){
    return `<select ${attrs}>${(e.choix || []).map(c => `<option value="${escapeAttr(c)}"${c === brut ? " selected" : ""}>${escapeHtml(t("cc_cfg_lang_" + c))}</option>`).join("")}</select>`;
  }
  if(e.type === "booleen"){
    return `<select ${attrs}><option value="true"${brut === "true" ? " selected" : ""}>${escapeHtml(t("cc_cfg_oui"))}</option><option value="false"${brut === "false" ? " selected" : ""}>${escapeHtml(t("cc_cfg_non"))}</option></select>`;
  }
  if(e.type === "fuseau"){
    // Lot « rr-fuseau-reglage » : un champ texte relié à la liste des fuseaux (la seule `datalist` de la page).
    return `<input type="text" ${attrs} size="40" maxlength="500" spellcheck="false" list="cc-cfg-fuseaux" value="${escapeAttr(brut)}">`
      + `<datalist id="cc-cfg-fuseaux">${(e.fuseaux || []).map(z => `<option value="${escapeAttr(z)}"></option>`).join("")}</datalist>`;
  }
  return `<input type="text" ${attrs} size="40" maxlength="500" spellcheck="false" value="${escapeAttr(brut)}">`;
}

function commandCfgDiffere(e){
  const brut = Object.prototype.hasOwnProperty.call(commandCfgChamps, e.cle) ? commandCfgChamps[e.cle] : commandCfgTexte(e);
  return String(brut).trim() !== commandCfgTexte(e).trim();
}

// L'incompatibilité : le modèle choisi (qui diffère) est dans la liste et n'accepte pas l'effort ENREGISTRÉ.
function commandCfgIncompatible(e){
  if(e.cle !== "ANTHROPIC_MODEL" || !commandCfgDiffere(e)) return false;
  const liste = commandCfgListe(), eff = commandCfgElement("ANTHROPIC_EFFORT");
  if(!liste || !eff) return false;
  const m = liste.find(x => x.id === String(commandCfgChamps[e.cle]).trim());
  return !!m && !m.efforts.includes(commandCfgTexte(eff));
}

// Ce qui décide de la cellule « Action » : le champ diffère, et l'incompatibilité (la cellule ne se redessine que si cela change).
function commandCfgEtatAction(e){
  return (commandCfgDiffere(e) ? "1" : "0") + (commandCfgIncompatible(e) ? "i" : "");
}

// Un champ numérique que le navigateur ne sait pas lire (`validity.badInput` : sa valeur est alors vide) ; un champ vidé exprès n'en est pas un.
function commandCfgIllisible(depuis){
  const champ = depuis.closest("tr").querySelector('[data-act="cfg-champ"]');
  return !!(champ && champ.type === "number" && champ.validity && champ.validity.badInput);
}

function commandCfgBouton(act, cle, libelle, classes, dis){
  return `<button type="button" class="btn btn-sm ${classes} cc-act" data-act="${act}" data-cle="${escapeAttr(cle)}"${dis ? " disabled" : ""}>${escapeHtml(libelle)}</button>`;
}

// La cellule « Action » d'une ligne en clair : « Enregistrer » et « Annuler » quand le champ diffère (jamais « Revenir au
// défaut » alors) ; « Revenir au défaut » seul au repos quand le réglage est renseigné, sauf le modèle (son défaut est vide, et
// un modèle vide ferme le Récit). Un modèle incompatible avec l'effort enregistré : « Enregistrer » désactivé et sa raison dessous.
function commandCfgActionClairHtml(e, occupe){
  if(commandCfgDiffere(e)){
    const inc = commandCfgIncompatible(e);
    const raison = inc ? `<div class="cc-hint">${escapeHtml(escFill(t("cc_cfg_effort_incompatible"), {effort: t("cc_cfg_effort_" + commandCfgTexte(commandCfgElement("ANTHROPIC_EFFORT")))}))}</div>` : "";
    return commandCfgBouton("cfg-save", e.cle, t("cc_cfg_enregistrer"), "btn-accent", occupe || inc)
      + commandCfgBouton("cfg-annuler", e.cle, t("cc_rights_cancel"), "", occupe) + raison;
  }
  return e.rempli && e.cle !== "ANTHROPIC_MODEL" ? commandCfgBouton("cfg-defaut", e.cle, t("cc_cfg_defaut"), "", occupe) : "";
}

function commandCfgSecretValeurHtml(e, occupe){
  if(commandCfgSecret === e.cle){
    return `<input type="password" class="cc-set" data-act="cfg-secret-champ" data-cle="${escapeAttr(e.cle)}" autocomplete="new-password" spellcheck="false" maxlength="500" aria-label="${escapeAttr(t("cc_cfg_l_" + e.cle))}"${occupe ? " disabled" : ""}>`;
  }
  const etat = !e.rempli ? `<span class="cc-office">${escapeHtml(t("cc_cfg_s_vide"))}</span>`
    : e.lisible ? `<span class="cc-office porte">${escapeHtml(t("cc_cfg_s_rempli"))}</span>`
    : `<span class="cc-office">${escapeHtml(t("cc_cfg_s_illisible"))}</span>`;
  let qui = "";
  if(e.rempli && e.maj_le){
    qui = e.maj_par == null
      ? escFill(t("cc_cfg_s_repris"), {date: fmtLocalDate(e.maj_le)})
      : escFill(t("cc_cfg_s_modifie"), {date: fmtLocalDate(e.maj_le) + " · " + fmtLocalTime(e.maj_le), nom: commandCfgNom(e.maj_par)});
  }
  return etat + (qui ? `<div class="cc-hint">${escapeHtml(qui)}</div>` : "");
}

function commandCfgSecretActionHtml(e, occupe){
  if(commandCfgSecret === e.cle){
    return commandCfgBouton("cfg-secret-save", e.cle, t("cc_cfg_enregistrer"), "btn-accent", true)
      + commandCfgBouton("cfg-secret-annuler", e.cle, t("cc_rights_cancel"), "", occupe);
  }
  const sansCle = !COMMAND_CFG.cle_presente;
  return commandCfgBouton("cfg-secret-ouvrir", e.cle, t(e.rempli ? "cc_cfg_remplacer" : "cc_cfg_saisir"), "", occupe || sansCle)
    + (e.rempli ? commandCfgBouton("cfg-vider", e.cle, t("cc_cfg_vider"), "", occupe) : "");
}

function commandCfgCell(cle, html, extra = ""){
  return `<td data-label="${escapeAttr(t(cle))}"${extra}>${html}</td>`;
}

// Sous le champ du modèle, à la place de la ligne du défaut : d'où vient la liste, ou pourquoi elle manque.
function commandCfgModeleAideHtml(){
  if(commandCfgListe()) return escapeHtml(t("cc_cfg_modeles_source"));
  if(COMMAND_CFG_MODELES && COMMAND_CFG_MODELES.raison === "cle") return escapeHtml(t("cc_cfg_modeles_sans_cle"));
  const d = COMMAND_CFG_MODELES && typeof COMMAND_CFG_MODELES.detail === "string" ? COMMAND_CFG_MODELES.detail : "";
  return escapeHtml(t("cc_cfg_modeles_erreur")) + (d ? "<br>" + escapeHtml(escFill(t("cc_cfg_modeles_detail"), {detail: d})) : "");
}

// Une ligne de réglage, suivie de la note « Vider » quand elle est armée sur elle (la ligne et sa suite, comme les livrées).
function commandCfgLigneHtml(e){
  const occupe = commandCfgOccupe.has(e.cle);
  const note = commandCfgNote && commandCfgNote.kind === "vider" && commandCfgNote.cle === e.cle ? commandCfgNote : null;
  const reglage = `<div>${escapeHtml(t("cc_cfg_l_" + e.cle))}</div><div class="cc-hint">${escapeHtml(t("cc_cfg_h_" + e.cle))}</div><code class="ref-cle">${escapeHtml(e.cle)}</code>`;
  const valeur = e.secret ? commandCfgSecretValeurHtml(e, occupe)
    : `${commandCfgChampHtml(e, occupe)}<div class="cc-hint">${e.cle === "ANTHROPIC_MODEL" ? commandCfgModeleAideHtml() : commandCfgDefautHtml(e)}</div>`;
  const action = e.secret ? commandCfgSecretActionHtml(e, occupe) : commandCfgActionClairHtml(e, occupe);
  let h = `<tr data-cfg="${escapeAttr(e.cle)}"${note ? ' class="sqn-liv-edition"' : ""}>`
    + commandCfgCell("cc_cfg_col_reglage", reglage) + commandCfgCell("cc_cfg_col_valeur", valeur) + commandCfgCell("cc_cfg_col_action", action, e.secret ? "" : ` data-diff="${commandCfgEtatAction(e)}"`) + `</tr>`;
  if(note){
    h += `<tr class="sqn-liv-suite"><td colspan="3" data-label="${escapeAttr(t("cc_cfg_col_reglage"))}">${ccConfirmHtml({
      titre: t("cc_cfg_vider_titre"),
      texte: escapeHtml(escFill(t("cc_cfg_vider_texte"), {reglage: t("cc_cfg_l_" + e.cle)})),
      err: note.err, danger: true, annuler: "cfg-note-annuler", ok: "cfg-vider-ok", libelle: t("cc_cfg_vider"), occupe: !!note.occupe,
    })}</td></tr>`;
  }
  return h;
}

function commandCfgRegHtml(){
  const cfg = COMMAND_CFG;
  let corps = "", groupe = null;
  cfg.reglages.forEach(e => {
    if(e.groupe !== groupe){
      groupe = e.groupe;
      corps += `<tr class="cc-group"><td colspan="3" data-label="${escapeAttr(t("cc_cfg_col_reglage"))}"><span class="cc-group-label">${escapeHtml(t(CFG_GROUPES[groupe] || groupe))}</span></td></tr>`;
    }
    corps += commandCfgLigneHtml(e);
  });
  return `<h3 class="cc-sub">${escapeHtml(t("cc_cfg_reg_title"))}</h3>`
    + (cfg.cle_presente ? "" : `<div class="cc-note deny">${escapeHtml(t("cc_cfg_cle_absente"))}</div>`)
    + `<div class="cc-wrap"><table class="cc-table"><thead><tr><th>${escapeHtml(t("cc_cfg_col_reglage"))}</th><th>${escapeHtml(t("cc_cfg_col_valeur"))}</th><th>${escapeHtml(t("cc_cfg_col_action"))}</th></tr></thead><tbody>${corps}</tbody></table></div>`;
}

// Les membres qui peuvent être nommés : ni fondateur ni nommé (les deux listes de /administrateurs, seules : `is_admin` de
// COMMAND_MEMBERS est périmé après un geste) ; triés par nom.
function commandCfgCandidats(){
  const deja = new Set(COMMAND_CFG_ADM.fondateurs.concat(COMMAND_CFG_ADM.nommes).map(a => String(a.id)));
  return (COMMAND_MEMBERS || []).filter(m => !deja.has(String(m.id)))
    .sort((a, b) => callsign(a.name).localeCompare(callsign(b.name)));
}

function commandCfgAdmHtml(){
  const d = COMMAND_CFG_ADM;
  const note = commandCfgNote && commandCfgNote.kind !== "vider" ? commandCfgNote : null;
  const lignes = d.fondateurs.map(f => `<tr>${commandCfgCell("cc_cfg_adm_col_nom", escapeHtml(commandCfgNom(f.id)))}`
    + commandCfgCell("cc_cfg_adm_col_statut", `<span class="cc-office porte">${escapeHtml(t("cc_cfg_adm_fondateur"))}</span>`)
    + commandCfgCell("cc_cfg_adm_col_depuis", "—")
    + commandCfgCell("cc_cfg_col_action", `<span class="cc-hint">${escapeHtml(t("cc_cfg_adm_fondateur_note"))}</span>`) + `</tr>`).join("");
  const nommes = d.nommes.map(n => {
    const arme = note && note.kind === "retirer" && String(note.id) === String(n.id);
    let h = `<tr${arme ? ' class="sqn-liv-edition"' : ""}>${commandCfgCell("cc_cfg_adm_col_nom", escapeHtml(commandCfgNom(n.id)))}`
      + commandCfgCell("cc_cfg_adm_col_statut", `<span class="cc-office">${escapeHtml(t("cc_cfg_adm_nomme"))}</span>`)
      + commandCfgCell("cc_cfg_adm_col_depuis", escapeHtml(n.nomme_le ? fmtLocalDate(n.nomme_le) : "—"))
      + commandCfgCell("cc_cfg_col_action", `<button type="button" class="btn btn-sm cc-act" data-act="cfg-adm-retirer" data-id="${escapeAttr(n.id)}"${note && note.occupe ? " disabled" : ""}>${escapeHtml(t("cc_cfg_adm_retirer"))}</button>`) + `</tr>`;
    if(arme){
      const soi = ME && String(n.id) === String(ME.id);
      h += `<tr class="sqn-liv-suite"><td colspan="4" data-label="${escapeAttr(t("cc_cfg_adm_col_nom"))}">${ccConfirmHtml({
        titre: t("cc_cfg_adm_retirer_titre"),
        texte: escapeHtml(escFill(t("cc_cfg_adm_retirer_texte"), {nom: commandCfgNom(n.id)})) + (soi ? " " + escapeHtml(t("cc_cfg_adm_retirer_soi")) : ""),
        err: note.err, danger: true, annuler: "cfg-note-annuler", ok: "cfg-retirer-ok", libelle: t("cc_cfg_adm_retirer"), occupe: !!note.occupe,
      })}</td></tr>`;
    }
    return h;
  }).join("");
  const occupe = !!(note && note.occupe);
  const options = commandCfgCandidats().map(m => `<option value="${escapeAttr(m.id)}"${String(m.id) === commandCfgChoix ? " selected" : ""}>${escapeHtml(callsign(m.name))}</option>`).join("");
  const nommer = note && note.kind === "nommer"
    ? `<div id="cc-cfg-adm-note">${ccConfirmHtml({
        titre: t("cc_cfg_adm_nommer_titre"),
        texte: escapeHtml(escFill(t("cc_cfg_adm_nommer_texte"), {nom: commandCfgNom(note.id)})),
        err: note.err, danger: false, annuler: "cfg-note-annuler", ok: "cfg-nommer-ok", libelle: t("cc_cfg_adm_nommer"), occupe,
      })}</div>` : "";
  return `<h3 class="cc-sub">${escapeHtml(t("cc_cfg_adm_title"))}</h3><p class="cc-hint">${escapeHtml(t("cc_cfg_adm_hint"))}</p>`
    + `<div class="cc-wrap"><table class="cc-table"><thead><tr><th>${escapeHtml(t("cc_cfg_adm_col_nom"))}</th><th>${escapeHtml(t("cc_cfg_adm_col_statut"))}</th><th>${escapeHtml(t("cc_cfg_adm_col_depuis"))}</th><th>${escapeHtml(t("cc_cfg_col_action"))}</th></tr></thead><tbody>${lignes}${nommes}</tbody></table></div>`
    + `<div class="cc-row"><select class="cc-set" data-act="cfg-adm-choix" aria-label="${escapeAttr(t("cc_cfg_adm_choisir"))}"${occupe ? " disabled" : ""}><option value="">${escapeHtml(t("cc_cfg_adm_choisir"))}</option>${options}</select>`
    + `<button type="button" class="btn btn-sm btn-accent cc-act" data-act="cfg-adm-nommer"${occupe || !commandCfgChoix ? " disabled" : ""}>${escapeHtml(t("cc_cfg_adm_nommer"))}</button></div>${nommer}`;
}

function renderCommandConfigAdm(){
  const box = $("#cc-cfg-adm");
  if(box && COMMAND_CFG_ADM) box.innerHTML = commandCfgAdmHtml();
}

function renderCommandConfig(){
  const box = $("#cc-cfg-fiche");
  if(!box) return;
  if(commandCfgLoadState === "loading" || commandCfgLoadState === "idle"){
    const rows = ["70%","90%","60%","85%","75%"].map((w,i)=>`<span class="skel" style="width:${w}"></span><span class="skel" style="width:${i%2?"55%":"80%"}"></span>`).join("");
    box.innerHTML = `<div class="cc-fiche">${rows}</div>`;
    return;
  }
  if(commandCfgLoadState === "error" || !COMMAND_CFG || !COMMAND_CFG_ADM){
    box.innerHTML = `<div class="cc-state"><div>${escapeHtml(t("cc_cfg_error"))}</div><div class="cc-state-act"><button type="button" class="btn btn-sm" data-act="cfg-retry">${escapeHtml(t("cc_camp_retry"))}</button></div></div>`;
    return;
  }
  box.innerHTML = `<p class="cc-hint">${escapeHtml(t("cc_cfg_hint"))}</p>`
    + `<div class="cc-block" id="cc-cfg-adm">${commandCfgAdmHtml()}</div>`
    + `<div class="cc-block" id="cc-cfg-reg">${commandCfgRegHtml()}</div>`
    + `<div class="cc-block" id="cc-cfg-dos">${commandCfgDossiersHtml()}</div>`;
}

// Lot « Les dossiers du serveur » : le bloc en lecture seule des trois dossiers branchés (rien ne s'y règle).
function commandCfgDossiersHtml(){
  const tete = `<h3 class="cc-sub">${escapeHtml(t("cc_cfg_dos_title"))}</h3><p class="cc-hint">${escapeHtml(t("cc_cfg_dos_hint"))}</p>`;
  if(!COMMAND_CFG_DOSSIERS) return tete + `<p class="cc-hint">${escapeHtml(t("cc_cfg_dos_erreur"))}</p>`;
  const loc = currentLang === "fr" ? "fr-FR" : "en-GB";
  const lignes = COMMAND_CFG_DOSSIERS.map(d => {
    const dossier = `<div>${escapeHtml(t("cc_cfg_dos_l_" + d.id))}</div><div class="cc-hint">${escapeHtml(t("cc_cfg_dos_h_" + d.id))}</div><code class="ref-cle">${escapeHtml(d.variable)}</code>`;
    let contenu;
    if(!d.present){
      contenu = `<span class="cc-office">${escapeHtml(t("cc_cfg_dos_absent"))}</span><div class="cc-hint">${escapeHtml(escFill(t("cc_cfg_dos_absent_aide"), {chemin: d.chemin}))}</div>`;
    } else if(d.fichiers === 0){
      const aide = d.id === "tuiles_gardees" ? escapeHtml(t("cc_cfg_dos_vide_aide_tuiles_gardees")) : escapeHtml(escFill(t("cc_cfg_dos_vide_aide"), {variable: d.variable}));
      contenu = `<span class="cc-office">${escapeHtml(t("cc_cfg_dos_vide"))}</span><div class="cc-hint">${aide}</div>`;
    } else {
      const cle = d.plafond ? "cc_cfg_dos_plafond" : (d.fichiers === 1 ? "cc_cfg_dos_un" : "cc_cfg_dos_n");
      contenu = `<span class="cc-office porte">${escapeHtml(escFill(t(cle), {n: Number(d.fichiers).toLocaleString(loc)}))}</span>`;
    }
    return `<tr data-dossier="${escapeAttr(d.id)}">` + commandCfgCell("cc_cfg_dos_col_dossier", dossier) + commandCfgCell("cc_cfg_dos_col_contenu", contenu) + `</tr>`;
  }).join("");
  return tete + `<div class="cc-wrap"><table class="cc-table"><thead><tr><th>${escapeHtml(t("cc_cfg_dos_col_dossier"))}</th><th>${escapeHtml(t("cc_cfg_dos_col_contenu"))}</th></tr></thead><tbody>${lignes}</tbody></table></div>`;
}

// La liste des modèles : jamais un rejet. Un échec (réseau, statut, forme) vaut « Anthropic n'a pas répondu » : la page reste entière.
async function commandCfgLireModeles(){
  try {
    const m = await apiFetch("/api/command/reglages/modeles");
    return m && typeof m.disponible === "boolean" && Array.isArray(m.modeles) ? m : CFG_MODELES_ERREUR;
  } catch(e){
    return CFG_MODELES_ERREUR;
  }
}

// Les dossiers branchés : jamais un rejet. Un échec (réseau, statut, corps sans liste `dossiers`) vaut `null` : la page s'ouvre quand même.
async function commandCfgLireDossiers(){
  try {
    const d = await apiFetch("/api/command/reglages/dossiers");
    return d && Array.isArray(d.dossiers) ? d.dossiers : null;
  } catch(e){
    return null;
  }
}

// Les deux lignes qui se répondent (le modèle borne l'effort, l'effort borne le modèle) se redessinent ensemble.
function commandCfgRedessinerRecit(){
  commandCfgRedessinerLigne("ANTHROPIC_MODEL");
  commandCfgRedessinerLigne("ANTHROPIC_EFFORT");
}

// La clé de l'API vient de changer : la liste se relit une fois, puis les lignes Modèle et Effort se redessinent.
async function commandCfgRelireModeles(){
  COMMAND_CFG_MODELES = await commandCfgLireModeles();
  commandCfgRedessinerRecit();
}

// Les membres : rien à lire s'ils le sont, un seul `GET` s'ils ne le sont pas (jamais un second pendant un `loading`, qu'on attend).
function commandCfgMembres(){
  if(commandMembersLoadState === "ready") return null;
  if(commandMembersLoadState === "loading"){
    return new Promise(fin => { const i = setInterval(() => { if(commandMembersLoadState !== "loading"){ clearInterval(i); fin(); } }, 100); });
  }
  return loadCommandMembers();   // idle ou error
}

// Les deux routes se lisent en parallèle, chacune une fois ; les membres viennent de COMMAND_MEMBERS s'il est prêt,
// sinon d'un loadCommandMembers() lancé en même temps (il ne rejette jamais : sans membres, le sélecteur reste vide).
async function loadCommandConfig(){
  commandCfgLoadState = "loading";
  renderCommandConfig();
  try {
    const [reg, adm, modeles, dossiers] = await Promise.all([
      apiFetch("/api/command/reglages"),
      apiFetch("/api/command/administrateurs"),
      commandCfgLireModeles(),
      commandCfgLireDossiers(),
      commandCfgMembres(),
    ]);
    COMMAND_CFG = reg;
    COMMAND_CFG_ADM = adm;
    COMMAND_CFG_MODELES = modeles;
    COMMAND_CFG_DOSSIERS = dossiers;
    commandCfgChamps = {}; commandCfgSecret = null; commandCfgOccupe = new Set(); commandCfgNote = null; commandCfgChoix = "";
    commandCfgLoadState = "ready";
    rrChargeFaite("configuration", "configuration");   // lot « La page Configuration du Centre » : ouverte par l'adresse
  } catch(e){
    commandCfgLoadState = "error";
    if(rrChargeRefusee("configuration", "configuration", e)) return;   // sans être administrateur : la 403 ramène à l'Escadre
  }
  renderCommandConfig();
}

function ensureCommandConfigLoaded(){
  if(commandCfgLoadState === "ready" || commandCfgLoadState === "loading") renderCommandConfig();
  else loadCommandConfig();
}

// La ligne seule se redessine (avec sa note « Vider » si elle est armée).
function commandCfgRedessinerLigne(cle){
  const e = commandCfgElement(cle);
  const tr = $("#cc-cfg-reg") ? $("#cc-cfg-reg").querySelector(`tr[data-cfg="${CSS.escape(cle)}"]`) : null;
  if(!e || !tr) return;
  const suite = tr.nextElementSibling;
  if(suite && suite.classList.contains("sqn-liv-suite")) suite.remove();
  tr.insertAdjacentHTML("afterend", commandCfgLigneHtml(e));
  tr.remove();
  if(commandCfgSecret === cle){
    const champ = $("#cc-cfg-reg").querySelector(`tr[data-cfg="${CSS.escape(cle)}"] input[data-act="cfg-secret-champ"]`);
    if(champ) champ.focus();
  }
}

// Arme (ou ferme) la note de la page : une seule à la fois ; l'ancienne et la nouvelle se redessinent.
function commandCfgPoserNote(nouvelle){
  const ancienne = commandCfgNote;
  commandCfgNote = nouvelle;
  [ancienne, nouvelle].forEach(n => {
    if(!n) return;
    if(n.kind === "vider") commandCfgRedessinerLigne(n.cle); else renderCommandConfigAdm();
  });
}

function commandCfgOuvrirSecret(cle){
  const avant = commandCfgSecret;
  commandCfgSecret = cle;
  if(avant && avant !== cle) commandCfgRedessinerLigne(avant);
  commandCfgRedessinerLigne(cle);
}

function commandCfgFermerSecret(){
  const avant = commandCfgSecret;
  commandCfgSecret = null;
  if(avant) commandCfgRedessinerLigne(avant);
}

// L'envoi d'une ligne : `PUT /reglages/<CLE>`. Pendant l'appel, les boutons et le champ de la ligne sont `disabled`.
// `valeur` (un secret compris) n'est gardée nulle part : elle ne vit que le temps de cet appel.
async function commandCfgEnvoyer(cle, valeur, note){
  if(commandCfgOccupe.has(cle)) return;
  commandCfgOccupe.add(cle);
  if(note) note.occupe = true;
  const tr = $("#cc-cfg-reg") ? $("#cc-cfg-reg").querySelector(`tr[data-cfg="${CSS.escape(cle)}"]`) : null;
  if(tr){
    const lignes = [tr];
    if(tr.nextElementSibling && tr.nextElementSibling.classList.contains("sqn-liv-suite")) lignes.push(tr.nextElementSibling);
    lignes.forEach(l => l.querySelectorAll("input, select, button").forEach(x => { x.disabled = true; }));
  }
  try {
    const el = await apiFetch("/api/command/reglages/" + encodeURIComponent(cle), {
      method: "PUT", headers: {"Content-Type": "application/json"}, body: JSON.stringify({valeur}),
    });
    const i = COMMAND_CFG.reglages.findIndex(x => x.cle === cle);
    if(i >= 0) COMMAND_CFG.reglages[i] = el;
    // Lot « rr-fuseau-reglage » (A6) : l'administrateur voit son changement sans recharger.
    if(cle === "REFERENCE_TZ" && ME) ME.fuseau = el.valeur || el.defaut || "Europe/Paris";
    delete commandCfgChamps[cle];
    if(commandCfgSecret === cle) commandCfgSecret = null;
    if(commandCfgNote === note) commandCfgNote = null;
    commandCfgOccupe.delete(cle);
    commandCfgRedessinerLigne(cle);
    // Le modèle borne l'effort et l'effort borne le modèle : les deux lignes se redessinent, une saisie en cours est gardée.
    if(cle === "ANTHROPIC_MODEL" || cle === "ANTHROPIC_EFFORT") commandCfgRedessinerRecit();
    showToast(t("cc_cfg_enregistre"));
    if(cle === "ANTHROPIC_API_KEY") commandCfgRelireModeles();
  } catch(e){
    commandCfgOccupe.delete(cle);
    if(note){
      note.occupe = false;
      note.err = commandCfgMessage(e);   // un refus de la confirmation reste dans sa note
    } else {
      showToast(e.status === 422 ? t("cc_cfg_err_valeur") : e.status === 409 ? t("cc_cfg_err_cle") : commandCfgMessage(e), "erreur");
    }
    commandCfgRedessinerLigne(cle);
    if(!note && e.status === 422){   // une valeur refusée : le focus revient sur le champ de la ligne redessinée
      const champ = $("#cc-cfg-reg") ? $("#cc-cfg-reg").querySelector(`tr[data-cfg="${CSS.escape(cle)}"] [data-act="cfg-champ"]`) : null;
      if(champ) champ.focus();
    }
  }
}

// Nommer et Retirer : la confirmation s'envoie, la liste se redessine depuis la réponse.
async function commandCfgAdmEnvoyer(b){
  const n = commandCfgNote;
  if(!n || n.occupe || n.kind === "vider") return;
  n.occupe = true;
  ccConfirmOccupe(b);
  $$("#cc-cfg-adm .cc-row select, #cc-cfg-adm .cc-row button, #cc-cfg-adm tbody button").forEach(x => { x.disabled = true; });
  try {
    const d = await apiFetch("/api/command/administrateurs/" + encodeURIComponent(n.id), {method: n.kind === "nommer" ? "PUT" : "DELETE"});
    COMMAND_CFG_ADM = d;
    commandCfgNote = null;
    if(n.kind === "nommer") commandCfgChoix = "";
    if(n.kind === "retirer" && ME && String(n.id) === String(ME.id)){
      // Ses propres droits : la page se recharge sur l'Escadre (l'onglet Configuration disparaît) ; l'entrée d'historique, qui
      // portait l'écran Configuration sans identifiant, est remplacée avant, sinon le rechargement la rejouerait.
      history.replaceState(null, "", location.pathname + location.search + "#centre");
      location.reload();
      return;
    }
    renderCommandConfigAdm();
  } catch(e){
    n.occupe = false;
    n.err = commandCfgMessage(e);
    renderCommandConfigAdm();
  }
}

function wireCommandConfigEvents(){
  const view = $("#view-cc-configuration");
  if(!view || view.dataset.wired) return; // câblage unique
  view.dataset.wired = "1";

  // Un champ en clair : la cellule « Action » se redessine (« Enregistrer » paraît quand le champ diffère) ; le champ garde le focus.
  const saisie = e => {
    const c = e.target.closest('[data-act="cfg-champ"]');
    if(c){
      const el = commandCfgElement(c.dataset.cle);
      if(!el) return;
      commandCfgChamps[el.cle] = c.value;
      // Seulement quand « Enregistrer » paraît ou disparaît (ou que l'incompatibilité change) : redessiner la cellule à chaque `change` (le départ du champ
      // au toucher du bouton) ferait perdre le clic.
      const td = c.closest("tr").querySelector("td:last-child"), diff = commandCfgEtatAction(el);
      if(td && td.dataset.diff !== diff){ td.innerHTML = commandCfgActionClairHtml(el, false); td.dataset.diff = diff; }
      return;
    }
    const s = e.target.closest('[data-act="cfg-secret-champ"]');
    if(s){
      const ok = s.closest("tr").querySelector('[data-act="cfg-secret-save"]');
      if(ok) ok.disabled = !s.value.trim();   // rien de ce qui est tapé n'est copié ailleurs
    }
  };
  view.addEventListener("input", saisie);
  view.addEventListener("change", e => {
    saisie(e);
    const sel = e.target.closest('[data-act="cfg-adm-choix"]');
    if(sel){
      if(commandCfgNote && commandCfgNote.occupe){ sel.value = commandCfgChoix; return; }   // un appel court : le choix ne bouge pas
      commandCfgChoix = sel.value;
      if(commandCfgNote && commandCfgNote.kind === "nommer") commandCfgPoserNote(null);
      else { const nommer = view.querySelector('[data-act="cfg-adm-nommer"]'); if(nommer) nommer.disabled = !commandCfgChoix; }
    }
  });

  view.addEventListener("keydown", e => {
    const c = e.target.closest('[data-act="cfg-champ"]');
    if(e.key === "Enter" && c && c.tagName === "INPUT"){
      e.preventDefault();
      const el = commandCfgElement(c.dataset.cle);
      if(el && commandCfgDiffere(el)){
        if(commandCfgIllisible(c)) showToast(t("cc_cfg_err_valeur"), "erreur");
        else commandCfgEnvoyer(el.cle, commandCfgChamps[el.cle]);
      }
      return;
    }
    const s = e.target.closest('[data-act="cfg-secret-champ"]');
    if(s && e.key === "Enter"){ e.preventDefault(); const ok = s.closest("tr").querySelector('[data-act="cfg-secret-save"]'); if(ok && !ok.disabled) ok.click(); }
    if(s && e.key === "Escape" && !commandCfgOccupe.has(s.dataset.cle)) commandCfgFermerSecret();
  });

  view.addEventListener("click", e => {
    const b = e.target.closest("[data-act]");
    if(!b || b.tagName === "INPUT" || b.tagName === "SELECT") return;
    const act = b.dataset.act, cle = b.dataset.cle;
    if(act === "cfg-retry"){ loadCommandConfig(); return; }
    if(act === "cfg-adm-nommer"){
      if(commandCfgChoix && !(commandCfgNote && commandCfgNote.occupe)) commandCfgPoserNote({kind: "nommer", id: commandCfgChoix, err: null, occupe: false});
      return;
    }
    if(act === "cfg-adm-retirer"){
      if(!(commandCfgNote && commandCfgNote.occupe)) commandCfgPoserNote({kind: "retirer", id: b.dataset.id, err: null, occupe: false});
      return;
    }
    if(act === "cfg-note-annuler"){ if(commandCfgNote && !commandCfgNote.occupe) commandCfgPoserNote(null); return; }
    if(act === "cfg-nommer-ok" || act === "cfg-retirer-ok"){ commandCfgAdmEnvoyer(b); return; }
    if(act === "cfg-vider"){
      if(commandCfgNote && commandCfgNote.occupe) return;
      if(commandCfgSecret) commandCfgFermerSecret();
      commandCfgPoserNote({kind: "vider", cle, err: null, occupe: false});
      return;
    }
    if(act === "cfg-vider-ok"){
      const n = commandCfgNote;
      if(n && n.kind === "vider" && !n.occupe){ ccConfirmOccupe(b); commandCfgEnvoyer(n.cle, null, n); }
      return;
    }
    if(act === "cfg-save"){
      const el = commandCfgElement(cle);
      if(!el || !commandCfgDiffere(el) || commandCfgIncompatible(el)) return;
      if(commandCfgIllisible(b)){ showToast(t("cc_cfg_err_valeur"), "erreur"); return; }   // un entier illisible : rien n'est envoyé
      const brut = Object.prototype.hasOwnProperty.call(commandCfgChamps, cle) ? commandCfgChamps[cle] : commandCfgTexte(el);
      commandCfgEnvoyer(cle, el.type === "booleen" ? brut === "true" : brut);
      return;
    }
    if(act === "cfg-annuler"){   // la saisie de la ligne est oubliée, la valeur enregistrée revient ; rien ne part
      if(!commandCfgOccupe.has(cle)){ delete commandCfgChamps[cle]; commandCfgRedessinerLigne(cle); }
      return;
    }
    if(act === "cfg-defaut"){ commandCfgEnvoyer(cle, null); return; }   // le défaut se remet d'un geste, sans confirmation
    if(act === "cfg-secret-ouvrir"){
      if(commandCfgNote && commandCfgNote.kind === "vider" && commandCfgNote.cle === cle) commandCfgPoserNote(null);
      commandCfgOuvrirSecret(cle);
      return;
    }
    if(act === "cfg-secret-annuler"){ commandCfgFermerSecret(); return; }
    if(act === "cfg-secret-save"){
      const champ = b.closest("tr").querySelector('[data-act="cfg-secret-champ"]');
      if(!champ || !champ.value.trim()) return;
      const valeur = champ.value;
      champ.value = "";   // le champ est vidé dès l'envoi, réussi ou non
      commandCfgEnvoyer(cle, valeur);
    }
  });
}


function goCommand(screen){
  // ⚠⚠ Lot 3.2b livré, recetté et accepté sans jamais pouvoir s'afficher,
  // pour cet exact oubli (liste littérale non mise à jour) -- la leçon la
  // plus chère de la phase. "droits" DOIT figurer ici (Lot 3.2d, P10).
  // "campagnes" ajouté au Lot 3.4, même exigence exacte.
  // "escadre" ajouté au lot « L'écran Escadre du Centre », même exigence exacte.
  // "referentiels" ajouté au lot « Les référentiels : types et armes », même exigence exacte.
  // "archives" ajouté au lot « L'écran Archives du Centre », même exigence exacte.
  // "configuration" ajouté au lot « La page Configuration du Centre », même exigence exacte (et RR_MODULES.command.ecrans).
  ["escadre", "escadrilles", "membres", "droits", "campagnes", "referentiels", "archives", "configuration"].forEach(s=>{
    const el = $("#view-cc-"+s);
    if(el) el.classList.toggle("hidden", s!==screen);
  });
  $$('[data-module-nav="command"] button[data-cc-nav]').forEach(b=>{
    b.classList.toggle("active", b.dataset.ccNav===screen);
  });
  // Lot « La charte commune de l'App » (v1.0079) : la ligne de la feuille « Plus » active, et « Plus » avec elle.
  let ligneActive = false;
  $$('#cc-plus-feuille [data-plus-vers]').forEach(b=>{
    const active = b.dataset.plusVers === screen;
    b.classList.toggle("active", active);
    if(active) ligneActive = true;
  });
  $$('[data-module-nav="command"] [data-plus]').forEach(b=> b.classList.toggle("active", ligneActive));
  fermerPlus();
  syncTopbarNavScroll();
  if(screen === "escadre") ensureCommandEscadreLoaded();
  if(screen === "escadrilles") ensureCommandSquadronsLoaded();
  if(screen === "membres"){
    ensureCommandMembersLoaded();
    loadCommandRelances(); // lot « Les relances » (R8) : la liste se relit à l'entrée
  }
  if(screen === "droits") ensureCommandRightsLoaded();
  if(screen === "campagnes") ensureCommandCampaignsLoaded();
  if(screen === "referentiels") ensureCommandRefLoaded();
  if(screen === "configuration") ensureCommandConfigLoaded();
  else commandCfgFermerSecret();   // lot « La page Configuration du Centre » : aucune valeur tapée ne reste dans un champ caché
  if(screen === "archives") ensureCommandArchivesLoaded();
  else if(commandAgentJeton){
    // Lot « La réception du .rrlog de l'agent » : le jeton quitte l'écran quand on quitte l'onglet Archives.
    commandAgentJeton = null;
    if(commandArchLoadState === "ready") renderCommandArchives();
  }
}


// Lot « La charte commune de l'App » (v1.0079) : ferme la feuille « Plus » de la barre du Centre.
function fermerPlus(){
  const feuille = $("#cc-plus-feuille");
  if(feuille) feuille.classList.remove("ouverte");
  $$('[data-module-nav="command"] [data-plus]').forEach(b=> b.setAttribute("aria-expanded", "false"));
}

function wireCommandNav(){
  $$('[data-module-nav="command"] button[data-cc-nav]').forEach(b=>{
    b.addEventListener("click", ()=>{
      goCommand(b.dataset.ccNav);
      rrPile("command", [{e:b.dataset.ccNav}]);   // lot « Le retour et l'adresse » : un onglet remplace l'entrée du module
    });
  });
  // Lot « La charte commune de l'App » (v1.0079) : « Plus » ouvre la feuille des trois onglets qui débordent.
  const feuillePlus = $("#cc-plus-feuille");
  $$('[data-module-nav="command"] [data-plus]').forEach(b=>{
    b.addEventListener("click", (e)=>{
      e.stopPropagation();
      const ouverte = feuillePlus.classList.toggle("ouverte");
      b.setAttribute("aria-expanded", ouverte ? "true" : "false");
    });
  });
  $$('#cc-plus-feuille [data-plus-vers]').forEach(b=>{
    b.addEventListener("click", ()=>{
      goCommand(b.dataset.plusVers);
      rrPile("command", [{e:b.dataset.plusVers}]);   // lot « Le retour et l'adresse » : idem
    });
  });
  document.addEventListener("click", (e)=>{
    if(!e.target.closest("#cc-plus-feuille")) fermerPlus();
  });
  const retryBtn = $("#cc-sqn-retry");
  if(retryBtn) retryBtn.addEventListener("click", loadCommandSquadrons);
  const mbrRetryBtn = $("#cc-mbr-retry");
  if(mbrRetryBtn) mbrRetryBtn.addEventListener("click", loadCommandMembers);
  // Lot « L'appel » : le bouton est redessiné à chaque rendu -- écoute
  // déléguée au conteneur, posée une seule fois.
  const appelZone = $("#cc-mbr-appel");
  if(appelZone) appelZone.addEventListener("click", e=>{ if(e.target.closest("#cc-appel-btn")) lancerAppel(); });
  // Lot « Le Centre au doigt et à la charte » (R3) : le titre des relances plie et déplie la liste (zone redessinée à
  // chaque rendu : écoute déléguée, posée une seule fois).
  const relancesZone = $("#cc-mbr-relances");
  if(relancesZone) relancesZone.addEventListener("click", e=>{
    if(!e.target.closest('[data-act="relances-plier"]')) return;
    commandRelancesOuvert = !commandRelancesOuvert;
    renderCommandRelances();
    // Addendum 1 (A3) : le bouton redessiné garde le focus.
    const titre = relancesZone.querySelector('[data-act="relances-plier"]');
    if(titre) titre.focus({preventScroll: true});
  });
  // R2 : la recherche de membre filtre à la frappe.
  const mbrQ = $("#cc-mbr-q");
  if(mbrQ) mbrQ.addEventListener("input", ccFiltrerMembres);
  const rightsRetryBtn = $("#cc-droits-retry");
  if(rightsRetryBtn) rightsRetryBtn.addEventListener("click", loadCommandRights);
  const campRetryBtn = $("#cc-camp-retry");
  if(campRetryBtn) campRetryBtn.addEventListener("click", loadCommandCampaigns);
  wireCommandSquadronsEvents();
  wireCommandRightsEvents();
  wireCommandCampaignsEvents();
  wireCommandEscadreEvents();
  wireCommandRefEvents();
  wireCommandArchivesEvents();
  wireCommandConfigEvents();
}

function wireDebriefNav(){
  $$('[data-module-nav="debrief"] button[data-nav]').forEach(b=>{
    b.addEventListener("click", ()=> goDebrief(b.dataset.nav, {reset:true}));
  });
  $$('[data-nav]').forEach(el=>{
    if(el.closest('[data-module-nav="debrief"]')) return; // déjà câblé ci-dessus
    el.addEventListener("click", ()=> goDebrief(el.dataset.nav));
  });
  $$("[data-open-session]").forEach(el=>{
    el.addEventListener("click", ()=> goDebrief("session"));
  });
  $$("[data-open-flight]").forEach(el=>{
    el.addEventListener("click", ()=> goDebrief("flight"));
  });
  wireMissionsMount();
  wireSessionMount();
  wireModalDeposer();
  wireFlightMount();
  wireModalReport();
}

/* Nav ‹ › contextuelle à `currentView` (Lot 4 §2) : ± 1 mois en vue Mois,
   ± 1 semaine (navigable) en vue Semaine — auparavant toujours ± 1 mois,
   y compris en vue Semaine où la semaine affichée restait de toute façon
   figée sur "aujourd'hui". */
async function onCalNav(delta){
  if(currentView === "month"){
    calMonth += delta;
    if(calMonth<0){ calMonth=11; calYear--; }
    if(calMonth>11){ calMonth=0; calYear++; }
  } else {
    weekAnchor = new Date(weekAnchor);
    weekAnchor.setDate(weekAnchor.getDate() + delta*7);
  }
  await fetchAndRenderCalendar();
}

/* ---------- Render depuis le cache (pas de fetch) ---------- */
function renderAll(){
  const app=$("#screen-app"); if(app && !app.dataset.module) app.dataset.module="planif";
  renderFilterChips();
  renderMonthGrid();
  renderWeekStrip();
  if(hebdoData) renderHebdo();
  renderAVenir();   // Lot « La Planification en grand écran » (v1.0077) : le panneau suit la langue et la Planche, sans requête
}

/* ===================================================================
   Lot « Le retour et l'adresse » (v1.0101) — l'adresse de chaque écran et l'historique du navigateur
   (ARU-30 le retour d'Android quitte la Ready Room ; ARU-31 aucun lien profond).

   L'ADRESSE d'un écran est le fragment de l'URL, jamais un chemin : `#<module>/<écran>/<arguments…>`.
   Les identifiants s'écrivent par encodeURIComponent et se lisent par decodeURIComponent ; une date s'écrit
   AAAA-MM-JJ. Les stations n'ont aucun fragment.

   L'HISTORIQUE porte exactement UNE ENTRÉE PAR NIVEAU au-dessus de celle des stations : le module (son onglet
   courant), puis chaque écran empilé de l'Escadre (`debriefStack` au-delà de sa racine), puis la fenêtre ouverte.
   Chaque entrée porte un état de l'App, dans `history.state` :
       { rr:1, mod:"planif"|"debrief"|"command"|null (stations),
         pile:[{e:<nom de l'écran>, …identifiants}, …]   // du module vers l'écran affiché ; les stations : []
         fen:null | {t:<nom de la fenêtre>, …}           // fiche, jour, creation, edition, deposer, rapport
         seul:true }                                      // posé quand aucune entrée de l'App n'est au-dessous
   Le retour d'Android, celui du navigateur et ‹ prennent le même chemin : `history.back()`, puis `popstate`, qui
   dessine l'écran que décrit l'état (rrHistorique). Toute fermeture de fenêtre par le code consomme son entrée.

   POUR AJOUTER UN ÉCRAN (le point d'enregistrement, §2.7) : une entrée dans `ecrans` du module, dans la table
   RR_MODULES ci-dessous, et rien dans le routeur, qui ne connaît aucun écran par son nom. Une entrée dit :
     seg     le segment d'adresse (par défaut le nom de l'écran) ;
     args    les noms des arguments qui suivent le segment, dans l'ordre : ce sont des champs de l'élément de pile ;
     pile    (a) → les éléments de pile à reconstruire quand l'adresse est lue (du bas vers l'écran) ; par défaut, l'écran seul ;
     racine  l'onglet où l'on retombe quand la charge de l'écran répond une erreur 4xx ;
     item    () → l'élément de pile de l'écran affiché (lit les identifiants courants) ;
     pose    (élément) → reprend les identifiants d'un élément avant de montrer l'écran.
   Le module dit `seg` (son préfixe), `court` (l'écran dont l'adresse s'écrit sans segment : le premier onglet),
   `montre(pile)` (dessine l'écran du haut de la pile, sans toucher à l'historique) et `refus()` (les droits).
   Un écran qui se charge par une route appelle `rrChargeRefusee(nom, id, e)` dans l'échec de son chargeur et
   `rrChargeFaite(nom, id)` à sa réussite. `rrAdresseEcran(module, écran, arguments)` rend l'adresse d'un écran :
   `rrAdresseEcran("debrief", "session", {id})` → `#debrief/session/<id>` (pour les liens que l'Escadre écrira).
   =================================================================== */
const RR_MODULES = {
  planif: {
    seg: "planif", court: "planche",
    ecrans: {
      planche: {},
      hebdo: {},
    },
    // Une fenêtre qui a une adresse : la fiche d'une occurrence (la Planche dessous).
    fenetres: {
      fiche: {seg: "evenement", args: ["ev", "date"], valide: a=> rrDateValide(a.date), pile: ()=> [{e:"planche"}]},
    },
    montre: pile=>{
      const vue = pile[pile.length - 1].e;
      if(currentAppView !== vue) switchAppView(vue);
      renderAll();
    },
    refus: ()=> null,
  },
  debrief: {
    seg: "debrief", court: "accueil",
    ecrans: {
      accueil: {},
      pilotes: {seg: "dossier"},
      campagnes: {},
      missions: {},
      escadrilles: {},
      campagne: {
        args: ["id"], racine: "campagnes",
        pile: a=> [{e:"campagnes"}, {e:"campagne", id:a.id}],
        item: ()=> ({e:"campagne", id:CURRENT_CAMPAIGN_ID}), pose: it=>{ CURRENT_CAMPAIGN_ID = it.id; },
      },
      escadrille: {
        args: ["id"], racine: "escadrilles",
        pile: a=> [{e:"escadrilles"}, {e:"escadrille", id:a.id}],
        item: ()=> ({e:"escadrille", id:CURRENT_SQUADRON_ID}), pose: it=>{ CURRENT_SQUADRON_ID = it.id; },
      },
      membre: {
        args: ["id"], racine: "escadrilles",
        pile: a=> [{e:"escadrilles"}, {e:"membre", id:a.id}],
        item: ()=> ({e:"membre", id:CURRENT_MEMBER_ID}), pose: it=>{ CURRENT_MEMBER_ID = it.id; },
      },
      session: {
        args: ["id"], racine: "missions",
        pile: a=> [{e:"missions"}, {e:"session", id:a.id}],
        item: ()=> ({e:"session", id:CURRENT_SESSION_ID}), pose: it=>{ CURRENT_SESSION_ID = it.id; },
      },
      flight: {
        seg: "vol", args: ["s", "id"], racine: "missions",
        pile: a=> [{e:"missions"}, {e:"session", id:a.s}, {e:"flight", s:a.s, id:a.id}],
        item: ()=> ({e:"flight", s:CURRENT_SESSION_ID, id:CURRENT_FLIGHT_ID}),
        pose: it=>{ CURRENT_SESSION_ID = it.s; CURRENT_FLIGHT_ID = it.id; },
      },
    },
    montre: pile=>{
      debriefStack = pile.map(x=> x.e);
      pile.forEach(x=>{ const ec = RR_MODULES.debrief.ecrans[x.e]; if(ec.pose) ec.pose(x); });
      renderDebrief(pile[pile.length - 1].e);
    },
    refus: ()=>{
      if((ME.capabilities||[]).includes("debrief.access")) return null;
      return ()=> showToast(t("debrief_construction_toast"), "erreur");
    },
  },
  command: {
    seg: "centre", court: "escadre",
    ecrans: {
      escadre: {}, escadrilles: {}, membres: {}, droits: {}, campagnes: {}, referentiels: {}, archives: {},
      // Lot « La page Configuration du Centre » : sans argument, l'écran porte un `id` de pile pour que `rrChargeRefusee`
      // (la 403 d'un non-administrateur) le retrouve ; l'adresse reste `#centre/configuration`.
      configuration: {racine: "escadre", pile: ()=> [{e: "configuration", id: "configuration"}]},
    },
    montre: pile=> goCommand(pile[pile.length - 1].e),
    refus: ()=>{
      if((ME.capabilities||[]).includes("command.access")) return null;
      return ()=>{ if(commandChefSansRole()) toastChefSansRole("erreur"); };   // sans le droit : rien, sauf le chef désigné sans le rôle
    },
  },
};

// Les fenêtres : `o` est le cadre (#modal-overlay, #modal-deposer, #modal-report), `montre(f)` dit si le cadre ouvert
// montre déjà cette fenêtre, `ouvre(f, adresse)` l'ouvre (adresse : ouverte par l'adresse ou l'historique).
const RR_FEN = {
  fiche: {o:"overlay",
    montre: f=> currentModalMode === "view" && String(currentModalEventId) === String(f.ev) && currentModalOccDate === f.date,
    ouvre: (f, adresse)=> openEventModal(f.ev, f.date, adresse ? {adresse:true} : undefined)},
  jour: {o:"overlay", montre: f=> currentModalMode === "day" && currentDayDate === f.date, ouvre: f=> openDayModal(f.date)},
  creation: {o:"overlay", montre: ()=> currentModalMode === "create", ouvre: f=> openCreateModal(f.date || undefined)},
  // L'édition ne se redessine pas seule (elle lit la fiche ouverte) : un état d'édition rouvre la fiche (rrFenNorm).
  edition: {o:"overlay", montre: ()=> currentModalMode === "edit", ouvre: f=> openEventModal(f.ev, f.date)},
  deposer: {o:"deposer", montre: ()=> true, ouvre: f=> openModalDeposer(f.camp || null)},
  rapport: {o:"report", montre: ()=> true, ouvre: ()=> openModalReport()},
};
const RR_CADRES = {overlay:"modal-overlay", deposer:"modal-deposer", report:"modal-report"};

const RR = {etat:null, garde:null, enDessin:false, pret:false};
// `etat` : l'état logique de l'historique (ce qu'il sera quand les gestes en file seront joués) ; `garde` : l'écran ouvert
// par l'adresse ou l'historique dont la charge est attendue ; `enDessin` : le dessin d'un état ne touche pas l'historique.
const RRH = {file:[], tourne:false, attente:null};

function rrDateValide(d){
  return /^\d{4}-\d{2}-\d{2}$/.test(String(d)) && new Date(d + "T00:00:00Z").toISOString().slice(0, 10) === d;
}
function rrEtat(mod, pile, fen, seul){
  const e = {rr:1, mod: mod || null, pile: mod ? pile : [], fen: fen || null};
  if(seul) e.seul = true;
  return e;
}
function rrEtatValide(s){
  if(!s || s.rr !== 1) return false;
  if(s.mod === null) return true;
  const m = RR_MODULES[s.mod];
  return !!m && Array.isArray(s.pile) && s.pile.length > 0 && s.pile.every(x=> x && m.ecrans[x.e]);
}
function rrMemeEtat(a, b){ return JSON.stringify([a.mod, a.pile, a.fen]) === JSON.stringify([b.mod, b.pile, b.fen]); }
function rrMemeFen(a, b){ return JSON.stringify(a || null) === JSON.stringify(b || null); }
function rrItem(mod, nom){ const ec = RR_MODULES[mod].ecrans[nom]; return ec.item ? ec.item() : {e:nom}; }

/* ---------- L'adresse ---------- */
function rrAdresseEcran(mod, nom, a){
  const m = RR_MODULES[mod], ec = m && (m.ecrans[nom] || (m.fenetres || {})[nom]);
  if(!ec) return "";
  let h = "#" + m.seg;
  if(nom !== m.court){
    h += "/" + (ec.seg || nom);
    (ec.args || []).forEach(k=>{ h += "/" + encodeURIComponent(String(a && a[k] != null ? a[k] : "")); });
  }
  return h;
}
function rrAdresseEtat(et){
  if(!et || !et.mod) return "";
  const m = RR_MODULES[et.mod];
  if(et.fen && m.fenetres && m.fenetres[et.fen.t]) return rrAdresseEcran(et.mod, et.fen.t, et.fen);
  const haut = et.pile[et.pile.length - 1];
  return haut ? rrAdresseEcran(et.mod, haut.e, haut) : "";
}
function rrUrl(et){ return location.pathname + location.search + rrAdresseEtat(et); }

// Lit une adresse : {mod:null} (rien), {mod:null, introuvable} (module inconnu), ou {mod, pile, fen, introuvable?}.
// Un écran inconnu d'un module connu, un segment manquant ou une date illisible : le premier onglet, `introuvable`.
function rrLire(hash){
  let segs;
  try { segs = String(hash || "").replace(/^#/, "").split("/").filter(s=> s !== "").map(decodeURIComponent); }
  catch(e){ return {mod:null, introuvable:true}; }
  if(!segs.length) return {mod:null};
  const nomMod = Object.keys(RR_MODULES).find(k=> RR_MODULES[k].seg === segs[0]);
  if(!nomMod) return {mod:null, introuvable:true};
  const m = RR_MODULES[nomMod];
  const premier = {mod:nomMod, pile:[{e:m.court}], fen:null};
  if(segs.length === 1) return premier;
  const toutes = Object.keys(m.ecrans).map(n=> ["e", n, m.ecrans[n]])
    .concat(Object.keys(m.fenetres || {}).map(n=> ["f", n, m.fenetres[n]]));
  const cible = toutes.find(([, n, ec])=> (ec.seg || n) === segs[1]);
  if(!cible) return Object.assign({introuvable:true}, premier);
  const [genre, nom, ec] = cible, args = ec.args || [], reste = segs.slice(2);
  if(reste.length !== args.length) return Object.assign({introuvable:true}, premier);
  const a = {}; args.forEach((k, i)=>{ a[k] = reste[i]; });
  if(ec.valide && !ec.valide(a)) return Object.assign({introuvable:true}, premier);
  if(genre === "f") return {mod:nomMod, pile:ec.pile(a), fen:Object.assign({t:nom}, a)};
  return {mod:nomMod, pile: ec.pile ? ec.pile(a) : [Object.assign({e:nom}, a)], fen:null};
}

/* ---------- L'historique : les gestes se jouent un à un (un parcours attend son popstate) ---------- */
function rrHEnfiler(op){
  RRH.file.push(op);
  if(RRH.tourne) return;
  RRH.tourne = true;
  const suite = ()=>{
    while(RRH.file.length){
      let r;
      try { r = RRH.file.shift()(); } catch(e){ r = null; }
      if(r && typeof r.then === "function"){ r.then(suite, suite); return; }
    }
    RRH.tourne = false;
    // La file est vide : l'état logique rejoint l'état réel de l'entrée courante (le drapeau `seul` compris).
    const s = history.state;
    if(rrEtatValide(s)) RR.etat = s;
  };
  suite();
}
// Un parcours (history.go) rend la main au popstate qui le suit ; `dessine` : l'écran change alors par ce popstate.
function rrHParcours(delta, dessine){
  rrHEnfiler(()=> new Promise(fin=>{
    const a = {dessine, fin, minuteur:null};
    a.minuteur = setTimeout(()=>{ if(RRH.attente === a){ RRH.attente = null; fin(); } }, 800);
    RRH.attente = a;
    try { history.go(delta); } catch(e){ clearTimeout(a.minuteur); RRH.attente = null; fin(); }
  }));
}
// Lot « Les liens de la soirée » (v1.0107, addendum 1) : une entrée posée par un lien (`lien:true`) porte plusieurs niveaux
// de pile en une seule entrée ; chaque entrée poussée au-dessus d'elle porte `sur:n` (n entrées la séparent de l'entrée du
// lien). Ainsi un recul sait jusqu'où il peut descendre avant de quitter l'écran visé (rrConsommer). `tel` : l'état est
// reposé tel quel, sans calculer ce compteur.
function rrPousser(et, tel){
  const L = RR.etat;
  if(!tel && L && L.mod && et.mod && et.lien == null && et.sur == null && (L.lien || L.sur)) et = Object.assign({}, et, {sur: (L.lien ? 0 : L.sur) + 1});
  RR.etat = et;
  rrHEnfiler(()=>{ try { history.pushState(et, "", rrUrl(et)); } catch(e){ /* historique indisponible : on se tait */ } });
}
function rrRemplacer(et){
  // Lot « Les liens de la soirée » : l'entrée remplacée reste ce qu'elle est dans la famille d'un lien (`lien` ou `sur`).
  const L0 = RR.etat;
  if(et.mod && et.lien == null && et.sur == null && L0 && L0.mod){
    if(L0.lien) et = Object.assign({}, et, {lien:true});
    else if(L0.sur) et = Object.assign({}, et, {sur: L0.sur});
  }
  RR.etat = et;
  rrHEnfiler(()=>{
    try {
      const cur = history.state;
      let e2 = (et.mod && !et.seul && cur && cur.rr === 1 && cur.seul) ? Object.assign({}, et, {seul:true}) : et;
      // Lot « Les liens de la soirée » (v1.0107) : l'entrée remplacée garde son origine (`lien`), comme son drapeau `seul`.
      if(et.mod && !et.lien && cur && cur.rr === 1 && cur.lien) e2 = Object.assign({}, e2, {lien:true});
      history.replaceState(e2, "", rrUrl(e2));
    } catch(e){ /* idem */ }
  });
}
// L'état du niveau d'en dessous : sans la fenêtre, puis sans l'écran empilé, puis les stations.
function rrDessous(et){
  if(et.fen) return rrEtat(et.mod, et.pile, null);
  if(et.pile.length > 1) return rrEtat(et.mod, et.pile.slice(0, -1), null);
  return rrEtat(null, []);
}
// Consomme `k` entrées : l'historique revient k niveaux plus bas, sans dessiner (l'écran, lui, est déjà au bon endroit).
function rrConsommer(k){
  const L = RR.etat;
  if(!L || k <= 0) return;
  let et = L;
  for(let i = 0; i < k; i++) et = rrDessous(et);
  if(L.seul){ rrRemplacer(et.mod ? Object.assign({}, et, {seul:true}) : et); return; }   // rien au-dessous : sur place
  // Lot « Les liens de la soirée » (v1.0107, addendum 1) : l'entrée au-dessous de l'entrée d'un lien est l'écran d'origine,
  // pas le niveau d'en dessous de la pile. `e` : les entrées qui séparent l'état de l'entrée du lien. Un recul d'au plus `e`
  // entrées se joue comme d'habitude ; un recul qui irait plus bas s'arrête sur l'entrée du lien et la remplace sur place
  // (elle garde `lien` : ‹ ramène à l'origine, qui reste où elle est).
  if(L.lien || L.sur){
    const e = L.lien ? 0 : L.sur;
    if(k <= e){
      RR.etat = Object.assign({}, et, k === e ? {lien:true} : {sur: e - k});
      rrHParcours(-k, false);
      return;
    }
    if(e > 0) rrHParcours(-e, false);
    rrRemplacer(et.mod ? Object.assign({}, et, {lien:true}) : et);
    return;
  }
  RR.etat = et;
  rrHParcours(-k, false);
}
// Met l'historique d'équerre avec la pile voulue (une entrée par niveau). Les gestes : ajouter (un écran de plus),
// consommer (un lien vers un écran déjà dans la pile, un onglet pris au fond de la pile), remplacer (un autre onglet).
function rrPile(mod, pile){
  RR.garde = null;
  let L = RR.etat || rrEtat(null, []);
  if(L.fen){ rrConsommer(1); L = RR.etat; }
  let base;
  if(L.mod === mod){
    const anc = L.pile;
    let c = 0;
    while(c < anc.length && c < pile.length && anc[c].e === pile[c].e) c++;
    base = Math.max(c, 1);
    rrConsommer(anc.length - base);
    const cible = rrEtat(mod, pile.slice(0, base));
    if(!rrMemeEtat(RR.etat, cible)) rrRemplacer(cible);
  } else if(L.mod){   // d'un module à un autre (le Centre → une fiche membre de l'Escadre) : le niveau du module est remplacé
    rrConsommer(L.pile.length - 1);
    rrRemplacer(rrEtat(mod, pile.slice(0, 1)));
    base = 1;
  } else {            // depuis les stations
    base = 0;
  }
  for(let i = base; i < pile.length; i++) rrPousser(rrEtat(mod, pile.slice(0, i + 1)));
}
// Une fenêtre s'ouvre : une entrée de plus ; si une fenêtre est déjà ouverte, la nouvelle garde son niveau (remplace).
function rrFenetreOuverte(f){
  if(RR.enDessin) return;
  const L = RR.etat;
  if(!L || !L.mod) return;
  if(rrMemeFen(L.fen, f)) return;
  const et = rrEtat(L.mod, L.pile, f, L.fen && L.seul);
  if(L.fen && L.lien) et.lien = true;   // lot « Les liens de la soirée » : la fenêtre qui en remplace une garde l'origine
  if(L.fen) rrRemplacer(et); else rrPousser(et);
}
// Une fenêtre se ferme, par n'importe quel chemin : son entrée est consommée.
function rrFenetreFermee(o){
  if(RR.enDessin) return;
  const L = RR.etat;
  if(!L || !L.fen || !RR_FEN[L.fen.t] || RR_FEN[L.fen.t].o !== o) return;
  // Lot « Les liens de la soirée » (v1.0107) : la fiche ouverte depuis une session (`lien`) : sa croix fait ce que fait ‹,
  // elle ramène à l'écran d'origine (l'entrée au-dessous n'est pas la Planche).
  if(L.lien && !L.seul){ rrHParcours(-1, true); return; }
  rrConsommer(1);
}

/* ---------- Lot « Les liens de la soirée » (v1.0107) : d'un module à l'autre par un lien ----------
   Un lien (la ligne d'une soirée sur la fiche, la note d'une session) ouvre l'écran visé avec sa pile entière et ajoute
   UNE seule entrée à l'historique : l'état porte la pile entière et `lien:true` (l'entrée au-dessous est l'écran
   d'origine, d'un autre module). ‹ et le retour du navigateur font alors la même chose : un pas en arrière, et l'état
   de l'entrée d'origine se dessine tel qu'il était. */
function rrOuvrirLien(arr){
  if(!arr || !arr.mod || arr.introuvable) return;
  const m = RR_MODULES[arr.mod];
  const refus = m && m.refus ? m.refus() : null;
  if(refus){ refus(); return; }
  const et = rrEtat(arr.mod, arr.pile, arr.fen);
  et.lien = true;
  rrPousser(et);
  rrAfficher(et);
}

/* ---------- Dessiner un état ---------- */
function rrFenOuverte(o){ const el = document.getElementById(RR_CADRES[o]); return !!el && !el.classList.contains("hidden"); }
function rrPeutFermer(o){
  if(o === "overlay") return !(rrConfirmCourante && rrConfirmCourante.enCours);
  if(o === "deposer") return !deposerBusy;
  return true;
}
function rrFermerUI(o){
  if(o === "overlay") closeModal();
  else if(o === "deposer") closeModalDeposer();
  else closeModalReport();
}
function rrFermerMenus(){
  const menu = $("#settings-menu");
  if(menu){ menu.classList.remove("open"); $("#settings-btn").setAttribute("aria-expanded", "false"); }
  const lc = $("#landing-theme-control");
  if(lc){ lc.classList.remove("open"); $("#landing-settings-btn").setAttribute("aria-expanded", "false"); }
  fermerPlus();
}
function rrFenNorm(et){
  const f = et.fen;
  if(!f || !RR_FEN[f.t]) return null;
  if(f.t === "edition") return {t:"fiche", ev:f.ev, date:f.date};
  if(f.t === "rapport" && !(CURRENT_SESSION && String(CURRENT_SESSION.id) === String(CURRENT_SESSION_ID))) return null;
  return f;
}
// Dessine l'écran que décrit un état (module, pile, fenêtre), sans toucher à l'historique ; rend la fenêtre montrée.
// Toute fenêtre que l'état ne porte pas se ferme, et le menu des réglages et la feuille « Plus » se ferment.
function rrAfficher(et, opts){
  RR.enDessin = true;
  let fen = null;
  try {
    rrFermerMenus();
    const m = et.mod ? RR_MODULES[et.mod] : null;
    if(et.mod !== "command") commandCfgFermerSecret();   // lot « La page Configuration du Centre » : un autre module ou les stations
    if(m){
      $("#screen-app").dataset.module = et.mod;
      $("#screen-landing").classList.add("hidden");
      $("#screen-app").classList.remove("hidden");
      m.montre(et.pile);
      const haut = et.pile[et.pile.length - 1];
      const g = (haut && haut.id != null) ? {mod:et.mod, e:haut.e, id:haut.id} : null;
      RR.garde = g;
      if(g) setTimeout(()=>{ if(RR.garde === g) RR.garde = null; }, 20000);
      fen = (opts && opts.sansFen) ? null : rrFenNorm(et);
    } else {
      $("#screen-app").classList.add("hidden");
      $("#screen-landing").classList.remove("hidden");
    }
    Object.keys(RR_CADRES).forEach(o=>{
      if(fen && RR_FEN[fen.t].o === o) return;
      if(rrFenOuverte(o)) rrFermerUI(o);
    });
    if(fen){
      const d = RR_FEN[fen.t];
      if(!(rrFenOuverte(d.o) && d.montre(fen))) d.ouvre(fen, true);
    }
  } finally {
    RR.enDessin = false;
  }
  return fen;
}
// Un état de l'historique : les droits d'abord (un module refusé ramène aux stations, avec son message), puis le dessin.
function rrArriver(s){
  const m = s.mod ? RR_MODULES[s.mod] : null;
  const refus = m && m.refus ? m.refus() : null;
  if(refus){
    const st = rrEtat(null, []);
    RR.etat = st;
    rrAfficher(st);
    rrRemplacer(st);
    refus();
    return;
  }
  const f = rrAfficher(s);
  if(!rrMemeFen(f, s.fen)) rrRemplacer(rrEtat(s.mod, s.pile, f, s.seul));   // l'état dit plus que l'écran n'a pu montrer
}
// Ouvre une adresse lue (§2.4) : `reconstruire` bâtit une entrée par niveau au-dessus des stations ; sans lui (un
// fragment changé à la main), l'entrée courante devient celle de l'écran, et rien ne se bâtit au-dessous.
function rrOuvrirAdresse(arr, reconstruire){
  const stations = rrEtat(null, []);
  const message = arr.introuvable ? ()=> showToast(t("adresse_introuvable"), "erreur") : null;
  const m = arr.mod ? RR_MODULES[arr.mod] : null;
  const refus = m && m.refus ? m.refus() : null;
  if(!m || refus){
    RR.etat = stations;
    rrAfficher(stations);
    rrRemplacer(stations);
    if(refus) refus(); else if(message) message();   // un seul message par ouverture
    return;
  }
  if(reconstruire){
    rrRemplacer(stations);                  // l'entrée courante devient celle des stations
    rrPile(arr.mod, arr.pile);              // puis une entrée par niveau
    rrAfficher(rrEtat(arr.mod, arr.pile, null));
    if(arr.fen) RR_FEN[arr.fen.t].ouvre(arr.fen, true);   // la fenêtre ajoute sa propre entrée
  } else {
    RR.etat = rrEtat(arr.mod, arr.pile, arr.fen, true);
    const f = rrAfficher(RR.etat);
    rrRemplacer(rrEtat(arr.mod, arr.pile, f, true));
  }
  if(message) message();
}
// L'état d'une entrée de l'historique vient d'être atteint (retour, avance, rechargement ou lien).
function rrHistorique(s){
  if(!RR.pret) return;
  RR.garde = null;
  if(!rrEtatValide(s)){ rrOuvrirAdresse(rrLire(location.hash), false); return; }   // un fragment changé à la main
  // Une fenêtre qui ne peut pas se fermer (un dépôt en cours, une action qui court) : le retour ne ferme rien,
  // l'entrée de la fenêtre est reposée et l'écran ne bouge pas.
  const avant = RR.etat, f = s.fen;
  const bloque = Object.keys(RR_CADRES).find(o=> rrFenOuverte(o) && !(f && RR_FEN[f.t] && RR_FEN[f.t].o === o) && !rrPeutFermer(o));
  if(bloque && avant && avant.fen && s.mod){
    // Lot « Les liens de la soirée » (addendum 1) : l'état d'avant est reposé tel quel (module, pile, fenêtre, `lien`, `sur`),
    // jamais reconstruit à partir de l'entrée du dessous (qui peut être l'écran d'origine d'un lien).
    const tel = Object.assign({}, avant);
    delete tel.seul;
    rrPousser(tel, true);
    return;
  }
  RR.etat = s;
  rrArriver(s);
}
function rrPopstate(e){
  const a = RRH.attente;
  if(a){   // le parcours que le code a lancé : l'écran est déjà à jour, sauf pour ‹ (`dessine`)
    RRH.attente = null;
    clearTimeout(a.minuteur);
    if(a.dessine) rrHistorique(e.state);
    a.fin();
    return;
  }
  rrHistorique(e.state);
}
// ‹ (#back-to-landing) : l'écran change par popstate seulement, comme le retour d'Android et celui du navigateur.
// Seule exception : aucune entrée de l'App au-dessous (une adresse tapée à la main) : ‹ monte d'un niveau, sur place.
function rrRetour(){
  const L = RR.etat;
  if(!L || !L.mod) return;
  if(L.seul){
    const dessous = rrDessous(L);
    rrRemplacer(dessous.mod ? Object.assign({}, dessous, {seul:true}) : dessous);
    rrAfficher(dessous);
    return;
  }
  rrHParcours(-1, true);
}
// Au chargement, après loadMe() et la langue : l'état de l'entrée (un rechargement), sinon le fragment, sinon l'adresse
// gardée à la connexion, sinon les stations.
function rrInit(gardee){
  window.addEventListener("popstate", rrPopstate);
  RR.pret = true;
  const s = history.state;
  if(rrEtatValide(s)){ RR.etat = s; rrArriver(s); return; }
  RR.etat = rrEtat(null, []);
  rrOuvrirAdresse(rrLire(location.hash || gardee), true);
}
// Le chargeur d'un écran ouvert par l'adresse ou l'historique : une erreur 4xx (hors 401) ramène à la racine de son
// onglet, avec `adresse_introuvable` ; les entrées des niveaux retombés ne restent pas dans l'historique.
function rrChargeRefusee(nom, id, e){
  const g = RR.garde;
  if(!g || g.e !== nom || String(g.id) !== String(id)) return false;
  if(!e || !(e.status >= 400 && e.status < 500) || e.status === 401) return false;
  const m = RR_MODULES[g.mod], ec = m && m.ecrans[nom];
  if(!ec || !ec.racine) return false;
  RR.garde = null;
  showToast(t("adresse_introuvable"), "erreur");
  const racine = [{e: ec.racine}];
  rrPile(g.mod, racine);
  m.montre(racine);
  return true;
}
function rrChargeFaite(nom, id){
  const g = RR.garde;
  if(g && g.e === nom && String(g.id) === String(id)) RR.garde = null;
}

/* ---------- Landing (hub des stations) ---------- */
// Lot « Le Centre de Commandement dit ce qu'il fait » (R8) : le membre est-il chef désigné
// d'une escadrille active (`ME.command_rank`, `/api/me`) ? Sert à la tuile du Centre : sans
// `command.access`, un chef désigné la voit grisée au lieu de ne rien voir.
function commandChefSansRole(){
  return !!(ME && ME.command_rank && ME.command_rank.rank === "leader");
}
function toastChefSansRole(genre){
  showToast(t("cc_station_sans_role_toast").split("{squadron}").join(ME.command_rank.squadron), genre);   // lot « Le retour et l'adresse » : « erreur » à l'ouverture par l'adresse
}

function initLanding(){
  $("#discord-signin").addEventListener("click", ()=>{ window.location.href = "/auth/login"; });
  $("#station-planif-open").addEventListener("click", ()=>{
    $("#screen-app").dataset.module = "planif";
    $("#screen-landing").classList.add("hidden");
    $("#screen-app").classList.remove("hidden");
    // Lot « La charte commune de l'App » (v1.0079, R590) : la Planification s'ouvre toujours sur son premier onglet.
    if(currentAppView !== "planche") switchAppView("planche");
    renderAll();
    rrPile("planif", [{e:"planche"}]);   // lot « Le retour et l'adresse » : ouvrir un module ajoute une entrée
  });
  // Lot D2② : symétrique Débrief -- pose data-module="debrief", ouvre sur la
  // racine Missions (reset de pile systématique à l'ouverture).
  // v0.76 : gate cosmétique -- même si le bouton est réactivé via la
  // console, on revérifie ME.capabilities et on court-circuite (le vrai
  // gate est côté backend, cf. require_debrief_access dans app/api.py).
  $("#station-debrief-open").addEventListener("click", ()=>{
    if(!ME || !(ME.capabilities||[]).includes("debrief.access")){
      showToast(t("debrief_construction_toast"));
      return;
    }
    $("#screen-app").dataset.module = "debrief";
    $("#screen-landing").classList.add("hidden");
    $("#screen-app").classList.remove("hidden");
    goDebrief("accueil", {reset:true}); // Lot « L'écran B »
  });
  // Clic sur la tuile en dehors du bouton (zone désactivée) : même toast,
  // pas d'ouverture. Le bouton disabled gère déjà son propre cas (aucun
  // click natif émis), ce listener couvre le reste de la tuile.
  $("#station-tile-debrief").addEventListener("click", (e)=>{
    if(e.target && e.target.id === "station-debrief-open") return;
    if(!ME || !(ME.capabilities||[]).includes("debrief.access")){
      showToast(t("debrief_construction_toast"));
    }
  });
  // Lot 3.2b, Volet 2 : ouverture du Centre de Commandement, patron de
  // #station-debrief-open. Garde cosmétique sur ME.capabilities -- le vrai
  // gate est côté backend (require_command_access, app/capabilities.py).
  // Contrairement à la tuile Débrief, la tuile CC est ABSENTE (pas grisée)
  // pour qui n'a pas le droit (arbitrage n°10) : pas de toast dédié, un
  // clic via console sans le droit ne fait simplement rien.
  // Lot « Le Centre de Commandement dit ce qu'il fait » (R8) : sauf pour le chef désigné
  // sans le rôle des chefs, dont la tuile est montrée grisée -- un clic sur la tuile
  // (bouton compris) lui dit pourquoi, comme la tuile Débrief verrouillée.
  $("#station-command-open").addEventListener("click", (e)=>{
    if(commandChefSansRole() && !(ME.capabilities||[]).includes("command.access")){
      toastChefSansRole();
      e.stopPropagation(); // un seul toast : l'écouteur de la tuile ne le redit pas
      return;
    }
    if(!ME || !(ME.capabilities||[]).includes("command.access")) return;
    $("#screen-app").dataset.module = "command";
    $("#screen-landing").classList.add("hidden");
    $("#screen-app").classList.remove("hidden");
    goCommand("escadre");   // Lot « La charte commune de l'App » (v1.0079, R590) : le premier onglet
    rrPile("command", [{e:"escadre"}]);   // lot « Le retour et l'adresse » : ouvrir un module ajoute une entrée
  });
  $("#station-tile-command").addEventListener("click", ()=>{
    if(commandChefSansRole() && !(ME.capabilities||[]).includes("command.access")) toastChefSansRole();
  });
  // Lot D2② : retour contextuel au module actif. Planif -> landing (inchangé).
  // Debrief : pop d'un niveau si pile>1, sinon (racine Missions) -> landing.
  // Command (Lot 3.2b) : pas de pile de navigation à ce lot -> retour direct
  // au landing, comme la Planification, mais posé en branche explicite --
  // ne pas laisser le CC tomber dans la branche par défaut de la Planif.
  // Lot « Le retour et l'adresse » (v1.0101) : ‹ appelle history.back() ; l'écran change par popstate seulement, comme
  // le retour d'Android et celui du navigateur (rrRetour) : une fiche se ferme, un vol revient à sa session, un onglet
  // revient aux stations.
  $("#back-to-landing").addEventListener("click", rrRetour);
  // Le chip compte (topbar module) est purement informatif depuis le Lot 5
  // §4 : plus de handler de déconnexion ici (retiré, pas juste masqué) pour
  // éliminer tout risque de déco accidentelle. Le retour au menu se fait
  // déjà via `#back-to-landing` ; la déconnexion se fait désormais
  // exclusivement via `#landing-logout` sur le menu principal.
  // Lot « La défense de l'App exposée » (R7) : la déconnexion est un POST (plus un
  // lien qu'une page d'un autre site pourrait déclencher) ; on retourne à `/` quel
  // que soit le résultat, refus ou panne réseau compris.
  $("#landing-logout").addEventListener("click", ()=>{
    const retourAccueil = () => { window.location.href = "/"; };
    fetch("/auth/logout", {method: "POST"}).then(retourAccueil, retourAccueil);
  });
}

function computeToday(){
  const now = new Date();
  TODAY = {y: now.getFullYear(), m: now.getMonth(), d: now.getDate()};
}

/* ---------- Câblage statique (indépendant des données) ---------- */
function wireStaticUI(){
  // Lot 7 §3/§5 : contrôle segmenté 3 états, plusieurs instances possibles
  // (menu réglages app + topbar large + landing) -- câblage unique par
  // sélecteur commun [data-theme-pref], pas par id (id non-unique en cas
  // de plusieurs instances DOM).
  $$("[data-theme-pref]").forEach(btn=>{
    btn.addEventListener("click", ()=> setThemePref(btn.dataset.themePref));
  });
  $$(".lang-toggle button").forEach(b=> b.addEventListener("click", ()=> setLang(b.dataset.lang)));
  // Lot « Les liens de la soirée » (v1.0107) : un toucher, un clic ou Entrée sur une ligne de la soirée (fiche) ou sur un
  // lien de la soirée planifiée (session) ouvre l'autre écran, avec sa pile, en une entrée d'historique (rrOuvrirLien) ;
  // avec Ctrl, ⌘, Maj ou un autre bouton, le navigateur ouvre l'adresse à sa façon.
  document.addEventListener("click", (e)=>{
    if(e.defaultPrevented || e.button !== 0 || e.ctrlKey || e.metaKey || e.shiftKey || e.altKey) return;
    const a = e.target && e.target.closest ? e.target.closest("#fiche-soiree a.soiree-ligne, .soiree-note a") : null;
    if(!a) return;
    e.preventDefault();
    rrOuvrirLien(rrLire(a.getAttribute("href")));
  });
  $$('[data-module-nav="planif"] button').forEach(b=> b.addEventListener("click", ()=>{
    switchAppView(b.dataset.view);
    rrPile("planif", [{e:b.dataset.view}]);   // lot « Le retour et l'adresse » : un onglet remplace l'entrée du module
  }));

  // Lot 5 §C : menu réglages (langue+thème), non-large uniquement -- en
  // Large #settings-menu reste affiché inline en CSS, ce toggle est alors
  // sans effet visuel (classe .open ignorée par la règle Large). Fermeture
  // au clic extérieur / Échap, même pattern que les dropdowns existants
  // (#aircraft-dropdown/#game-dropdown/#map-dropdown, cf. plus bas).
  $("#settings-btn").addEventListener("click", ()=>{
    const menu = $("#settings-menu");
    const willOpen = !menu.classList.contains("open");
    menu.classList.toggle("open", willOpen);
    $("#settings-btn").setAttribute("aria-expanded", String(willOpen));
  });

  // Lot « Manuel : le bouton ? » : le « ? » de la barre ouvre le Manuel Pilote à la section de l'écran affiché ;
  // la touche « ? » fait de même, sauf pendant une saisie et sur la page d'accueil (landing).
  $("#help-btn").addEventListener("click", (e)=>{
    e.preventDefault();
    openManuel();
  });
  document.addEventListener("keydown", (e)=>{
    if(e.key !== "?" || e.ctrlKey || e.metaKey || e.altKey) return;
    const tg = e.target;
    if(tg && (tg.tagName === "INPUT" || tg.tagName === "TEXTAREA" || tg.tagName === "SELECT" || tg.isContentEditable)) return;
    const app = document.getElementById("screen-app");
    if(!app || app.classList.contains("hidden")) return;
    e.preventDefault();
    openManuel();
  });

  // Lot 7 §5 : roue dentée de la landing -- même patron (dropdown au clic,
  // toujours en mode dropdown ici, pas de variante "inline large" comme
  // pour la topbar : la landing n'a pas de palier large/compact à ce niveau).
  $("#landing-settings-btn").addEventListener("click", ()=>{
    const menu = $("#landing-theme-control");
    const willOpen = !menu.classList.contains("open");
    menu.classList.toggle("open", willOpen);
    $("#landing-settings-btn").setAttribute("aria-expanded", String(willOpen));
  });

  $("#month-prev").addEventListener("click", ()=> onCalNav(-1));
  $("#month-next").addEventListener("click", ()=> onCalNav(1));

  $$(".view-toggle button").forEach(b=> b.addEventListener("click", async ()=>{
    currentView = b.dataset.viewmode;
    $$(".view-toggle button").forEach(x=> x.classList.toggle("active", x===b));
    $("#cal-grid").classList.toggle("hidden", currentView!=="month");
    $("#agenda-list").style.display = currentView==="month" ? "" : "none";
    $("#week-strip").classList.toggle("hidden", currentView!=="week");
    await fetchAndRenderCalendar();
  }));

  $("#add-event-btn").addEventListener("click", openCreateModal);
  $("#modal-close").addEventListener("click", closeModal);
  $("#modal-secondary-close").addEventListener("click", closeModal);
  $("#modal-overlay").addEventListener("click", (e)=>{ if(e.target.id==="modal-overlay") closeModal(); });
  document.addEventListener("keydown",(e)=>{
    if(e.key==="Escape" && !$("#modal-overlay").classList.contains("hidden")) closeModal();
    if(e.key==="Escape" && !$("#modal-deposer").classList.contains("hidden")) closeModalDeposer();
    if(e.key==="Escape" && $("#modal-report") && !$("#modal-report").classList.contains("hidden")) closeModalReport();
    if(e.key==="Escape" && $("#settings-menu").classList.contains("open")){
      $("#settings-menu").classList.remove("open");
      $("#settings-btn").setAttribute("aria-expanded","false");
    }
    if(e.key==="Escape" && $("#landing-theme-control") && $("#landing-theme-control").classList.contains("open")){
      $("#landing-theme-control").classList.remove("open");
      $("#landing-settings-btn").setAttribute("aria-expanded","false");
    }
  });


  $("#modal-edit-btn").addEventListener("click", ()=>{
    if(!currentModalOccurrence) return;
    const scope = currentModalOccurrence.recurring ? $("#scope-select").value : "series";
    openEditModal(scope);
  });
  $("#modal-delete-btn").addEventListener("click", handleDelete);
  $("#modal-save-btn").addEventListener("click", submitEventForm);

  // v0.80 -- RSVP série : câblé une seule fois (comme les autres boutons de
  // modale ci-dessus), jamais dans une fonction de rendu (sinon empilement
  // de handlers à chaque re-render du contrôle RSVP).
  $("#rsvp-series-btn").addEventListener("click", async ()=>{
    if(!currentYourState) return;
    const btn = $("#rsvp-series-btn");
    btn.disabled = true;                     // anti double-clic (écriture de masse)
    try {
      const body = {event_id: currentModalEventId, occ_date: currentModalOccDate,
                    state: currentYourState, scope: "series"};
      if(rsvpPrefsVisible){
        body.aircraft = prefsAircraft;
        body.mission_types = prefsMissionTypes;
      }
      const res = await apiFetch("/api/presences", {
        method:"PUT", headers:{"Content-Type":"application/json"},
        body: JSON.stringify(body)
      });
      const n = (res && res.applied_count) || 0;
      showToast(n ? t("rsvp_series_done").replace("{n}", n) : t("rsvp_series_none"));
    } catch(e){
      showToast(t("error_generic"), "erreur");
    } finally {
      btn.disabled = false;
    }
  });

  // Lot 6 : sélecteur d'appareils (recherche + puces) -- ouverture/fermeture
  // du menu déroulant et filtre texte. Câblé une seule fois (statique) ;
  // le CONTENU des options est re-rendu à chaque frappe / ouverture par
  // renderAircraftOptions() (cf. plus haut).
  $("#aircraft-add-btn").addEventListener("click", ()=>{
    const dd = $("#aircraft-dropdown");
    const willOpen = dd.classList.contains("hidden");
    dd.classList.toggle("hidden");
    if(willOpen){
      $("#aircraft-filter").value = "";
      renderAircraftOptions();
      $("#aircraft-filter").focus();
    }
  });
  $("#aircraft-filter").addEventListener("input", ()=> renderAircraftOptions());
  document.addEventListener("click", (e)=>{
    const picker = $("#aircraft-picker");
    const dd = $("#aircraft-dropdown");
    if(picker && dd && !dd.classList.contains("hidden") && !picker.contains(e.target)){
      dd.classList.add("hidden");
    }
    // Lot 8 : même logique de fermeture pour le sélecteur jeu libre. La
    // modale (donc #game-picker) est recréée à chaque ouverture ; ce
    // listener global unique (câblé ici une seule fois) reste valable
    // car il requery le DOM à chaque clic plutôt que de garder une
    // référence figée.
    const gamePicker = $("#game-picker");
    const gameDd = $("#game-dropdown");
    if(gamePicker && gameDd && !gameDd.classList.contains("hidden") && !gamePicker.contains(e.target)){
      gameDd.classList.add("hidden");
    }
    // v0.23 : même logique de fermeture pour le sélecteur map.
    const mapPicker = $("#map-picker");
    const mapDd = $("#map-dropdown");
    if(mapPicker && mapDd && !mapDd.classList.contains("hidden") && !mapPicker.contains(e.target)){
      mapDd.classList.add("hidden");
    }
    // Lot 5 §C : même logique de fermeture pour le menu réglages.
    const settingsWrap = $("#settings-wrap");
    const settingsMenu = $("#settings-menu");
    if(settingsWrap && settingsMenu && settingsMenu.classList.contains("open") && !settingsWrap.contains(e.target)){
      settingsMenu.classList.remove("open");
      $("#settings-btn").setAttribute("aria-expanded","false");
    }
    // Lot 7 §5 : même logique de fermeture pour la roue dentée landing.
    const landingWrap = $("#landing-settings-wrap");
    const landingCtrl = $("#landing-theme-control");
    if(landingWrap && landingCtrl && landingCtrl.classList.contains("open") && !landingWrap.contains(e.target)){
      landingCtrl.classList.remove("open");
      $("#landing-settings-btn").setAttribute("aria-expanded","false");
    }
  });

  // Lot D2② : câblage statique de la nav Débrief (chrome/nav uniquement,
  // aucun contenu -- cf. wireDebriefNav()).
  wireDebriefNav();
  // Lot 3.2b : câblage statique de la nav Centre de Commandement.
  wireCommandNav();
}

/* Lot 8 : footer de version, non authentifié côté API (le footer doit
   s'afficher aussi sur l'écran de login -- cf. script inline dans
   login.html pour ce cas, qui duplique ce fetch minimal car app.js n'y
   est pas chargé). Échec silencieux (pas de footer plutôt qu'une erreur
   visible) : l'info n'est pas critique au fonctionnement de l'app. */
// Lot « rr-release-auto » (v1.0118) : une version qui commence par `RR-V` s'affiche telle quelle (`RR-V1.0.0+3`), une autre
// garde le `v` (`v1.0118`). Règle unique : le pied et les éléments `data-rr-version` passent par elle.
function versionAffichee(version){
  const v = String(version);
  return v.startsWith("RR-V") ? v : `v${v}`;
}

async function loadVersionFooter(){
  try {
    const res = await fetch("/api/version");
    if(!res.ok) return;
    const data = await res.json();
    const el = $("#app-version-footer");
    if(el && data && data.version) el.textContent = versionAffichee(data.version);
    // Lot « rr-marque-signature » : chaque élément `data-rr-version` reçoit le même texte que le pied.
    if(data && data.version) document.querySelectorAll("[data-rr-version]").forEach((e) => { e.textContent = versionAffichee(data.version); });
  } catch(e){ /* silencieux, cf. commentaire ci-dessus */ }
}

/* v0.76 -- Délégation globale du repli avatar (posée une seule fois, hors
   de toute fonction de rendu). Les événements `error` sur les ressources
   (<img>) ne remontent pas en bulle -- capture obligatoire (3e argument
   `true`). Couvre automatiquement les 3 usages actuels (#account-avatar,
   roster, day-roster) et tout usage futur d'avatarHtml(), sans câblage
   supplémentaire. */
document.addEventListener("error", (e) => {
  const el = e.target;
  // Lot « L'écran Escadre du Centre » : un emblème introuvable retombe sur le logo statique.
  if (el && el.tagName === "IMG" && el.dataset && el.dataset.wingEmblem != null && !el.src.endsWith(WING_STATIC_EMBLEM)) {
    el.src = WING_STATIC_EMBLEM;
    return;
  }
  if (el && el.tagName === "IMG" && el.dataset && el.dataset.avatarFallback != null) {
    const holder = el.parentNode;               // .avatar ou #account-avatar
    if (holder) holder.textContent = el.dataset.avatarFallback;
  }
}, true);

/* Lot « La config d'escadre préchargée » (v1.0050), règle changée au lot « La config d'escadre de Mission Plan
   fabriquée par le Centre » (v1.0091) : la config d'escadre n'est plus un fichier déposé à la main, la Ready Room la
   fabrique depuis le Centre de Commandement (`/outils/wing-config.json`) ; on l'écrit dans le navigateur sous
   `wing_config_v1`, la clé que lisent les modules de Mission Plan (même origine, même stockage). Règle : la config
   servie valide REMPLACE celle du navigateur dès que son texte (`JSON.stringify`) diffère de celui du navigateur, quel
   que soit le `wing.id` local (rien, JSON illisible, autre wing : on écrit) ; contenu identique -> rien. `fetch`
   direct, pas `apiFetch` : un `401` ne doit jamais renvoyer à l'accueil. Muette de bout en bout : ni toast, ni texte,
   aucune erreur ne remonte. Ne sert PAS à la Ready Room (`ME.wing`, `applyWingIdentity` ne la lisent pas).
   Lot « La config d'escadre recopiée juste après un enregistrement » (v1.0092) : `apiFetch` la relance, sans attente,
   après toute écriture réussie sous `/api/command/squadrons` ou `/api/command/wing`. */
async function syncWingConfigSuite(){
  const WING_CONFIG_KEY = "wing_config_v1";
  const isObj = (v) => v !== null && typeof v === "object" && !Array.isArray(v);
  const wingId = (cfg) => (isObj(cfg) && isObj(cfg.wing) && typeof cfg.wing.id === "string" && cfg.wing.id !== "") ? cfg.wing.id : null;
  try {
    const res = await fetch("/outils/wing-config.json", { credentials:"same-origin", cache:"no-cache" });
    if(res.status !== 200) return;
    const served = await res.json();
    if(!isObj(served) || served.configSchemaVersion !== 1 || wingId(served) === null || !Array.isArray(served.squadrons)) return;
    let current = null;
    try { current = JSON.parse(localStorage.getItem(WING_CONFIG_KEY)); } catch(e){ current = null; }
    const text = JSON.stringify(served);
    // Lot « La config d'escadre de Mission Plan fabriquée par le Centre » : la config servie REMPLACE celle du
    // navigateur dès que son texte diffère, quel que soit le `wing.id` local.
    if(current !== null && JSON.stringify(current) === text) return;  // déjà à jour
    try { localStorage.setItem(WING_CONFIG_KEY, text); } catch(e){ /* stockage plein ou indisponible : on se tait */ }
  } catch(e){ /* silencieux : aucune erreur ne remonte */ }
}

/* Lot « Le miroir des tuiles DCS » (v1.0059) : la Ready Room sert les tuiles de
   la couche « Carte DCS » à `/outils/tuiles/dcs/{key}/{z}/{x}/{y}.png` ; on
   écrit l'adresse dans le navigateur sous `map_layers_v1`, la clé que lit le
   Route Planner (même origine, même stockage) et qui remplace `{key}` par la clé
   d'Olympus du théâtre. Règle : si `map_layers_v1` n'est pas exactement le texte
   ci-dessous, on l'y écrit ; sinon, rien. Muette de bout en bout : ni `fetch`, ni
   toast, aucune autre clé touchée, un stockage indisponible se tait. */
function syncCartesSuite(){
  const MAP_LAYERS_KEY = "map_layers_v1";
  const text = JSON.stringify({ configSchemaVersion: 1, dcs: { url: "/outils/tuiles/dcs/{key}/{z}/{x}/{y}.png" } });
  try {
    if(localStorage.getItem(MAP_LAYERS_KEY) === text) return;
    localStorage.setItem(MAP_LAYERS_KEY, text);
  } catch(e){ /* stockage plein ou indisponible : on se tait */ }
}

/* ---------- Init ---------- */
async function init(){
  wireStaticUI();
  initPanneauAVenir();   // Lot « La Planification en grand écran » (v1.0077)
  initLanding();
  initInvitesBlock(); // lot « L'accès invité » (R12)
  loadVersionFooter();

  try {
    await loadMe();
  } catch(e){
    // apiFetch a déjà redirigé vers "/" (401) ; rien de plus à faire ici.
    return;
  }
  // Lot « Le retour et l'adresse » (v1.0101) : l'adresse que la page de connexion a gardée sert une fois ; la clé est
  // retirée à chaque chargement de l'App, qu'elle ait servi ou non.
  let adresseGardee = "";
  try { adresseGardee = sessionStorage.getItem("rr_adresse") || ""; sessionStorage.removeItem("rr_adresse"); } catch(e){ /* idem */ }
  // Lot « La config d'escadre préchargée » : lancée sans attente, juste après le
  // loadMe() réussi ; elle ne retarde aucun rendu et aucune de ses erreurs ne remonte.
  syncWingConfigSuite();
  // Lot « Le miroir des tuiles DCS » : juste après, sans attente ; muette.
  syncCartesSuite();
  applyWingIdentity(false); // lot « L'écran Escadre du Centre » : setLang(initialLang()) suit plus bas
  await loadLibelles(); // lot « Les référentiels » : avant tout rendu du Débrief

  // v0.36 (tag "NOUVEAU") : posé une seule fois ici, APRÈS loadMe() (donc
  // authentifié) -- `previous` = last_seen_at AVANT cet appel, qui vient
  // de le remettre à "maintenant" côté serveur. SINCE reste figé pour
  // toute la session : les tags posés à l'ouverture ne disparaissent qu'à
  // la prochaine visite (prochain rechargement/reconnexion), jamais en
  // cours de session. Échec silencieux (pas de tags plutôt qu'un crash
  // du bootstrap) : non critique au fonctionnement de l'app.
  // Lot « L'accès invité » (R11) : l'invité ne l'envoie pas (le serveur le refuserait), sans toast.
  try {
    const seen = estInviteEcran() ? null : await apiFetch("/api/seen", { method:"POST" });
    SINCE = seen && seen.previous ? new Date(seen.previous) : null;
  } catch(e){ SINCE = null; }

  renderAccountChip();
  $("#add-event-btn").classList.toggle("hidden", !(ME.capabilities||[]).includes("event.create"));

  // v0.76 -- Debrief "en chantier" : ME.capabilities n'est connu qu'ici
  // (après loadMe()), donc l'état de la tuile ne peut être posé avant.
  // Purement cosmétique (front) : le vrai gate est backend
  // (require_debrief_access, cf. app/api.py). État verrouillé seulement si
  // la capacité manque (arbitrage A1).
  {
    const hasDebriefAccess = (ME.capabilities||[]).includes("debrief.access");
    $("#station-tile-debrief").classList.toggle("station-locked", !hasDebriefAccess);
    $("#station-debrief-open").disabled = !hasDebriefAccess;
  }

  // v0.98 -- Centre de Commandement : la tuile est ABSENTE pour qui ne porte
  // pas `command.access` (spec Socle v1.1 §5.2, arbitrage n°10) -- ni grisée,
  // ni badgée. Elle naît `hidden` dans index.html et n'est révélée qu'ici,
  // après loadMe() : ME.capabilities n'est pas connu avant. Même patron que
  // #add-event-btn ci-dessus. Purement cosmétique : le vrai verrou est
  // `require_command_access` (app/capabilities.py), et aucune sécurité ne
  // repose sur l'absence d'un élément du DOM.
  // Lot « Le Centre de Commandement dit ce qu'il fait » (R8) : une seule exception à
  // l'absence -- le chef désigné qui ne porte pas le rôle Discord des chefs (Discord
  // fait foi, la garde ne change pas). Sa tuile est MONTRÉE, grisée (`station-locked`,
  // le patron de la tuile Débrief), « Ouvrir » désactivé, et dit pourquoi.
  {
    const hasCommandAccess = (ME.capabilities||[]).includes("command.access");
    const chefSansRole = !hasCommandAccess && commandChefSansRole();
    const tuileCc = $("#station-tile-command");
    tuileCc.classList.toggle("hidden", !hasCommandAccess && !chefSansRole);
    tuileCc.classList.toggle("station-locked", chefSansRole);
    $("#station-command-open").disabled = chefSansRole;
    // `data-i18n` suit le libellé : un changement de langue le retraduit comme les autres.
    const statutCc = tuileCc.querySelector(".station-status");
    statutCc.dataset.i18n = chefSansRole ? "cc_station_sans_role" : "status_operational";
    statutCc.textContent = t(statutCc.dataset.i18n);
  }

  computeToday();
  calYear = TODAY.y; calMonth = TODAY.m;
  weekAnchor = new Date(TODAY.y, TODAY.m, TODAY.d);
  hebdoAnchor = toISODate(new Date(TODAY.y, TODAY.m, TODAY.d));

  // Lot « La charte commune de l'App » (v1.0079) : un message d'erreur reste jusqu'à ce qu'on le touche.
  $("#toast").addEventListener("click", ()=>{
    const el = $("#toast");
    if(el.classList.contains("erreur")) el.classList.remove("show", "erreur");
  });

  themePref = initialThemePref();
  applyTheme();
  applyLayout();
  setLang(initialLang());
  connectSSE();

  // Lot « Le retour et l'adresse » (v1.0101, §2.4) : l'écran de l'état d'historique (rechargement), du fragment, de
  // l'adresse gardée ; sinon les stations.
  rrInit(adresseGardee);

  await fetchAndRenderCalendar();
  // Une journée rouverte par un rechargement s'est dessinée avant les données du calendrier : elle se redessine avec elles.
  if(currentModalMode === "day" && currentDayDate) openDayModal(currentDayDate);
  await refreshHebdo();
}

document.addEventListener("DOMContentLoaded", init);
})();
