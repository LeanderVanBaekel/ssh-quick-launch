# ssh-quick-launch

`ssh-quick-launch` is een kleine Python-tool die een curses-menu toont om snel SSH-sessies te starten en extra commando's uit te voeren. Hosts worden automatisch uit je `~/.ssh/config` gelezen aan de hand van speciale `# MENU:`-tags.

## Functies

- Overzichtelijk hoofdmenu waarin hosts per categorie worden weergegeven.
- Submenu (`c`) met veelgebruikte commando's of zelf gedefinieerde acties.
- Eenvoudige downloadbrowser (`d`) waarmee je bestanden kunt kopiëren of mappen laten zippen en downloaden.
- Zoekfilter: geef zoektermen mee op de commandline om het menu te beperken.

## Configuratie

Voeg tags toe aan je `~/.ssh/config` om hosts in het menu te tonen. Het formaat is:

```
# MENU: <Categorie> | <Label> | [optioneel custom commando]
Host <alias>
    HostName <server>
    User <gebruiker>
```

Voorbeeld:

```
# MENU: Demo | Webserver
Host demo
    HostName demo.example.com
    User ubuntu
```

Optioneel kun je een derde veld opgeven om een custom SSH-commando aan het submenu toe te voegen:

```
# MENU: Demo | Deploy | ssh deploy-script.sh
```

Alle `# MENU:`-regels tot aan de volgende lege regel of `Host`-sectie horen bij dezelfde host.

## Gebruik

Start het programma met:

```
./s [zoektermen]
```

Navigatie in het menu:

- Pijltjestoetsen om categorieën en hosts te kiezen.
- `Enter` logt direct in op de gekozen host.
- `c` opent het commando-submenu met je eigen en voorgedefinieerde acties.
- `d` opent de downloadbrowser.
- `q` sluit het programma.

### Downloadbrowser

Met `d` blader je door mappen op de server en kies je bestanden om te downloaden. Druk opnieuw op `d` op een map om deze eerst te zippen en vervolgens te downloaden.

### Zoekfilter

Geef één of meerdere termen mee bij het starten om het menu te filteren. Enkele afkortingen worden automatisch herkend (`dev` → `develop`, `stag` → `staging`, `prod` → `production`).

## Vereisten

- Python 3
- `ssh` en `scp` moeten beschikbaar zijn in je PATH

Installeer door het script `s` uitvoerbaar te maken en ergens in je PATH te plaatsen, bijvoorbeeld `~/bin/`.

