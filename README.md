# ssh-quick-launch

`ssh-quick-launch` is een kleine Python-tool die een curses-menu toont om snel SSH-sessies te starten en extra commando's uit te voeren. Hosts worden automatisch uit je `~/.ssh/config` gelezen aan de hand van speciale `# MENU:`-tags.

## Functies

- Overzichtelijk hoofdmenu waarin hosts per categorie worden weergegeven.
- Submenu (`c`) met veelgebruikte commando's of zelf gedefinieerde acties.
- Eenvoudige downloadbrowser (`d`) waarmee je bestanden kunt kopiëren of mappen laten zippen en downloaden.
- Eenvoudige uploadbrowser (`u`) om lokale bestanden of mappen naar de server te kopiëren of als zip te uploaden.
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

### Zelf updaten

Gebruik `./s --update` om de laatste versie binnen te halen. Met `./s --version`
bekijk je de huidige git-revisie.

Navigatie in het menu:

- Pijltjestoetsen om categorieën en hosts te kiezen.
- `Enter` logt direct in op de gekozen host.
- `c` opent het commando-submenu met je eigen en voorgedefinieerde acties.
- `d` opent de downloadbrowser.
- `u` opent de uploadbrowser.
- `q` sluit het programma.

### Downloadbrowser

Met `d` blader je door mappen op de server en kies je bestanden om te downloaden. Druk opnieuw op `d` op een map om deze eerst te zippen en vervolgens te downloaden.

### Uploadbrowser

Met `u` blader je door lokale mappen om bestanden te uploaden. Druk `d` op een map om deze te zippen en naar de server te kopiëren.

### Zoekfilter

Geef één of meerdere termen mee bij het starten om het menu te filteren. Enkele afkortingen worden automatisch herkend (`dev` → `develop`, `stag` → `staging`, `prod` → `production`).

## Vereisten

- Python 3
- `ssh` en `scp` moeten beschikbaar zijn in je PATH

## Installatie

1. Controleer of `~/bin` in je `PATH` staat:

   ```bash
   echo "$PATH" | tr ':' '\n'
   ```

   Zie je `$HOME/bin` niet staan? Voeg het dan toe in `~/.bashrc` of `~/.zshrc`:

   ```bash
   echo 'export PATH="$HOME/bin:$PATH"' >> ~/.bashrc  # of ~/.zshrc
   source ~/.bashrc  # of source ~/.zshrc
   ```

2. Zorg dat de map bestaat

   ```bash
   mkdir -p ~/bin
   ```
   
3. clone de repository op de plek waar je het wilt hebben, bijvoorbeeld in `~/src/ssh-quick-launch`:

   ```bash
   git clone <repository-url> ~/src/ssh-quick-launch
   ```

4. Navigeer naar de map waar de repository is gekloond en maak het script uitvoerbaar:
   ```bash
   cd ~/src/ssh-quick-launch
   chmod +x s
   ln -s "$PWD/s" ~/bin/s
   ```

Dankzij de symlink kun je overal `s` uitvoeren.

