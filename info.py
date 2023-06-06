""" Information and constants are put here and imported into app.py. """

party_colors = {
    "MP": "#83CF39",
    "V": "#b51a0e",
    "S": "#E8112d",
    "C": "#009933",
    "M": "#52BDEC",
    "KD": "#000077",
    "SD": "#DDDD00",
    "L": "#006AB3",
    "NYD": "#ffff2b",
    '': 'white',
    '-': 'white'
}

select_columns = '''
                talk_id,
                dok_id,
                "anforandetext" AS "Text", 
                anforande_nummer AS number, 
                kammaraktivitet as debatetype, 
                talare AS "Talare", 
                datum AS "Datum", 
                year AS År, 
                debateurl AS url_session, 
                parti AS "Parti",
                audiofileurl as url_audio,
                startpos as start,
                intressent_id
                '''






# 70 % lighter party colors.
party_colors_lighten = {
    "MP": '#daf1c4',
    "V": '#f8ada7',
    "S": '#fab6bf',
    "C": '#94ffb8',
    "M": '#cbebf9',
    "KD": "#b1b1ff", # 80 %
    "SD": "#ffffa8",
    "L": "#9cd6ff",
    "NYD": "#ffffbf",
    '': 'white',
    '-': 'white'
}

css = """ <style>
a:link {
  color: black;
}
a:visited {
  color: black;
}
a:hover {
  color: grey;
}
"""
for p, c in party_colors.items():
    if p == 'NYD':
        c = '#FFC000'
    if p == 'SD':
        c = '#E5AC00'
    if p in ['', '-']:
        c = 'black'
    css += f"\n.{p} a{{color: {c};}}"
css += '\n</style>'

# css = '''
#     <style>
#       .C a{
#         color: green;
#    }
#     </style>
# '''

months_conversion = {
    'januari': '01',
    'februari': '02',
    'mars': '03',
    'april': '04',
    'maj': '05',
    'juni': '06',
    'juli': '07',
    'augusti': '08',
    'september': '09',
    'oktober': '10',
    'november': '11',
    'december': '12'
    }
explainer = """Det här är en databas över vad svenska riksdagspolitiker har sagt i olika debatter i Riksdagen sedan 1993.
Datan kommer dels från data.riksdagen.se och dels från transkriberingar av vad som sänts i Riksdagens videotjänst (från år 2000).  
- Börja med att skriva ett eller flera sökord nedan. Du kan använda asterix (*), minus(-), citattecken (""), OR och år\:yyyy-yyyy. Sökningen    
`energikris* baskraft OR kärnkraft "fossilfria energikällor" -vindkraft år:2015-2022` söker anföranden som\:  
    - nämner "energikris" (inkl. ex. "energikris*en*")  
    - nämner antingen "baskraft" *eller* "kärnkraft"  
    - nämner den *exakta frasen* "fossilfria energikällor"  
    - *inte* nämner "vindkraft"  
    - återfinns under åren 2015-2022  
- När du fått dina resultat kan sedan klicka bort parier eller ändra vilka år och debatttyper du är intresserad av.
- Under "Längre utdrag" kan du välja att se hela anförandet i text, och under texten finns länkar till Riksdagens Webb-TV och nedladdningsbart ljud (i de fall
där debatten har sänts).  

Berätta gärna hur du skulle vilja använda datan och om sånt som inte funkar. [Mejla mig](mailto:lasse@edfast.se) eller [skriv till mig på Twitter](https://twitter.com/lasseedfast).  
Jag som gjort den här sidan heter [Lasse Edfast och är journalist](https://lasseedfast.se).
"""

debate_types = {
            "kam-vo": "Beslut",
            "bet": "Debatt om beslut",
            "kam-fs": "Frågestund",
            "kam-ar": "Information från regeringen",
            "ip": "Interpellationsdebatt",
            "kam-sf": "Statsministerns frågestund",
            "sam-ou": "Öppen utfrågning",
            "kam-ad": "Aktuell debatt",
            "kam-al": "Allmänpolitisk debatt",
            "kam-bu": "Budgetdebatt",
            'kam-bp': 'Bordläggning',
            'kam-pd': 'Partiledardebatt',
            'kam-dv': 'Debatt med anledning av vårpropositionen',
            'sam-se': 'Öppet seminarium',
            'kam-ud': 'Utrikespolitisk debatt'
        }

limit_warning = '''
        Din sökning ger fler än 10 000 träffar. Försök gör den mer specifik, exempelvis genom att
        använda minustecken eller specificera årtal genom att skriva år\:yyyy-yyyy (ex. år:2019-2020, utan mellanrum efter kolon).
        Gränsen på 10 000 träffar finns för att servern inte ska krascha och kommer att höjas när jag har en starkare server.
        '''