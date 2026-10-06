#ifndef GUARD_CONFIG_SPECIES_ENABLED_H
#define GUARD_CONFIG_SPECIES_ENABLED_H

// WARNING: For some reason, using 1/0 instead of TRUE/FALSE causes cry IDs to be shifted.
// Please use TRUE/FALSE when using the family toggles.

// Modifying the latest generation WILL change the saveblock due to Dex flags and will require a new save file.
// Generations of Pokémon are defined by the first member introduced,
// so Pikachu depends on the Gen 1 setting despite Pichu being the lowest member of the evolution tree.
// Eg: If P_GEN_2_POKEMON is set to FALSE, all members of the Sneasel Family will be disabled
// (Sneasel + Hisuian, Weavile and Sneasler).
#define P_GEN_1_POKEMON                  TRUE // Generation 1 Pokémon (RGBY)
#define P_GEN_2_POKEMON                  TRUE // Generation 2 Pokémon (GSC)
#define P_GEN_3_POKEMON                  TRUE // Generation 3 Pokémon (RSE, FRLG)
#define P_GEN_4_POKEMON                  TRUE // Generation 4 Pokémon (DPPt, HGSS)
#define P_GEN_5_POKEMON                  TRUE // Generation 5 Pokémon (BW, B2W2)
#define P_GEN_6_POKEMON                  TRUE // Generation 6 Pokémon (XY, ORAS)
#define P_GEN_7_POKEMON                  TRUE // Generation 7 Pokémon (SM, USUM, LGPE)
#define P_GEN_8_POKEMON                  TRUE // Generation 8 Pokémon (SwSh, BDSP, LA)
#define P_GEN_9_POKEMON                  TRUE // Generation 9 Pokémon (SV)

// Setting this to TRUE will add the new evolutions to the Regional Dex.
#define P_NEW_EVOS_IN_REGIONAL_DEX       TRUE

// Battle gimmick specific Forms.
#define P_MEGA_EVOLUTIONS                TRUE
#define P_PRIMAL_REVERSIONS              TRUE // Groudon and Kyogre only.
#define P_ULTRA_BURST_FORMS              TRUE // Ultra Necrozma only.
#define P_GIGANTAMAX_FORMS               FALSE // TREY: no Dynamax/Gigantamax (D19)
#define P_TERA_FORMS                     TRUE

// Fusion forms
#define P_FUSION_FORMS                   TRUE

// Regional Forms. Includes Regional Form evolutions, like Sirfetch'd.
#define P_REGIONAL_FORMS                 TRUE
#define P_ALOLAN_FORMS                   FALSE // TREY: no Alolan forms (D10)
#define P_GALARIAN_FORMS                 FALSE // TREY: no Galarian forms or their evolutions (D17)
#define P_HISUIAN_FORMS                  P_REGIONAL_FORMS // TREY: on, Hisuian forms in Sinnoh (D10)
#define P_PALDEAN_FORMS                  P_REGIONAL_FORMS // TREY: on, Paldean forms in Kitakami (D10)

// Big groups of forms that aren't always desired when choosing families.
#define P_PIKACHU_EXTRA_FORMS            TRUE
#define P_COSPLAY_PIKACHU_FORMS          P_PIKACHU_EXTRA_FORMS
#define P_CAP_PIKACHU_FORMS              P_PIKACHU_EXTRA_FORMS

// Cross-generation evolutions. Includes pre-evolutions.
#define P_CROSS_GENERATION_EVOS          TRUE
#define P_GEN_2_CROSS_EVOS               P_CROSS_GENERATION_EVOS
#define P_GEN_3_CROSS_EVOS               P_CROSS_GENERATION_EVOS
#define P_GEN_4_CROSS_EVOS               P_CROSS_GENERATION_EVOS
//#define P_GEN_5_CROSS_EVOS             // Gen 5 didn't introduce any cross-gen evos.
#define P_GEN_6_CROSS_EVOS               P_CROSS_GENERATION_EVOS // Just Sylveon.
//#define P_GEN_7_CROSS_EVOS             // Alolan evolutions handled by P_ALOLAN_FORMS.
#define P_GEN_8_CROSS_EVOS               P_CROSS_GENERATION_EVOS // Regional evolutions handled by P_GALARIAN_FORMS and P_HISUIAN_FORMS.
#define P_GEN_9_CROSS_EVOS               P_CROSS_GENERATION_EVOS // Clodsire handled by P_PALDEAN_FORMS.

// To disable specific families, replace P_GEN_x_POKEMON with FALSE.
#define P_FAMILY_BULBASAUR               P_GEN_1_POKEMON
#define P_FAMILY_CHARMANDER              P_GEN_1_POKEMON
#define P_FAMILY_SQUIRTLE                P_GEN_1_POKEMON
#define P_FAMILY_CATERPIE                P_GEN_1_POKEMON
#define P_FAMILY_WEEDLE                  P_GEN_1_POKEMON
#define P_FAMILY_PIDGEY                  P_GEN_1_POKEMON
#define P_FAMILY_RATTATA                 P_GEN_1_POKEMON
#define P_FAMILY_SPEAROW                 P_GEN_1_POKEMON
#define P_FAMILY_EKANS                   P_GEN_1_POKEMON
#define P_FAMILY_PIKACHU                 P_GEN_1_POKEMON
#define P_FAMILY_SANDSHREW               P_GEN_1_POKEMON
#define P_FAMILY_NIDORAN                 P_GEN_1_POKEMON
#define P_FAMILY_CLEFAIRY                P_GEN_1_POKEMON
#define P_FAMILY_VULPIX                  P_GEN_1_POKEMON
#define P_FAMILY_JIGGLYPUFF              P_GEN_1_POKEMON
#define P_FAMILY_ZUBAT                   P_GEN_1_POKEMON
#define P_FAMILY_ODDISH                  P_GEN_1_POKEMON
#define P_FAMILY_PARAS                   P_GEN_1_POKEMON
#define P_FAMILY_VENONAT                 P_GEN_1_POKEMON
#define P_FAMILY_DIGLETT                 P_GEN_1_POKEMON
#define P_FAMILY_MEOWTH                  P_GEN_1_POKEMON
#define P_FAMILY_PSYDUCK                 P_GEN_1_POKEMON
#define P_FAMILY_MANKEY                  P_GEN_1_POKEMON
#define P_FAMILY_GROWLITHE               P_GEN_1_POKEMON
#define P_FAMILY_POLIWAG                 P_GEN_1_POKEMON
#define P_FAMILY_ABRA                    P_GEN_1_POKEMON
#define P_FAMILY_MACHOP                  P_GEN_1_POKEMON
#define P_FAMILY_BELLSPROUT              P_GEN_1_POKEMON
#define P_FAMILY_TENTACOOL               P_GEN_1_POKEMON
#define P_FAMILY_GEODUDE                 P_GEN_1_POKEMON
#define P_FAMILY_PONYTA                  P_GEN_1_POKEMON
#define P_FAMILY_SLOWPOKE                P_GEN_1_POKEMON
#define P_FAMILY_MAGNEMITE               P_GEN_1_POKEMON
#define P_FAMILY_FARFETCHD               P_GEN_1_POKEMON
#define P_FAMILY_DODUO                   P_GEN_1_POKEMON
#define P_FAMILY_SEEL                    P_GEN_1_POKEMON
#define P_FAMILY_GRIMER                  P_GEN_1_POKEMON
#define P_FAMILY_SHELLDER                P_GEN_1_POKEMON
#define P_FAMILY_GASTLY                  P_GEN_1_POKEMON
#define P_FAMILY_ONIX                    P_GEN_1_POKEMON
#define P_FAMILY_DROWZEE                 P_GEN_1_POKEMON
#define P_FAMILY_KRABBY                  P_GEN_1_POKEMON
#define P_FAMILY_VOLTORB                 P_GEN_1_POKEMON
#define P_FAMILY_EXEGGCUTE               P_GEN_1_POKEMON
#define P_FAMILY_CUBONE                  P_GEN_1_POKEMON
#define P_FAMILY_HITMONS                 P_GEN_1_POKEMON
#define P_FAMILY_LICKITUNG               P_GEN_1_POKEMON
#define P_FAMILY_KOFFING                 P_GEN_1_POKEMON
#define P_FAMILY_RHYHORN                 P_GEN_1_POKEMON
#define P_FAMILY_CHANSEY                 P_GEN_1_POKEMON
#define P_FAMILY_TANGELA                 P_GEN_1_POKEMON
#define P_FAMILY_KANGASKHAN              P_GEN_1_POKEMON
#define P_FAMILY_HORSEA                  P_GEN_1_POKEMON
#define P_FAMILY_GOLDEEN                 P_GEN_1_POKEMON
#define P_FAMILY_STARYU                  P_GEN_1_POKEMON
#define P_FAMILY_MR_MIME                 P_GEN_1_POKEMON
#define P_FAMILY_SCYTHER                 P_GEN_1_POKEMON
#define P_FAMILY_JYNX                    P_GEN_1_POKEMON
#define P_FAMILY_ELECTABUZZ              P_GEN_1_POKEMON
#define P_FAMILY_MAGMAR                  P_GEN_1_POKEMON
#define P_FAMILY_PINSIR                  P_GEN_1_POKEMON
#define P_FAMILY_TAUROS                  P_GEN_1_POKEMON
#define P_FAMILY_MAGIKARP                P_GEN_1_POKEMON
#define P_FAMILY_LAPRAS                  P_GEN_1_POKEMON
#define P_FAMILY_DITTO                   P_GEN_1_POKEMON
#define P_FAMILY_EEVEE                   P_GEN_1_POKEMON
#define P_FAMILY_PORYGON                 P_GEN_1_POKEMON
#define P_FAMILY_OMANYTE                 P_GEN_1_POKEMON
#define P_FAMILY_KABUTO                  P_GEN_1_POKEMON
#define P_FAMILY_AERODACTYL              P_GEN_1_POKEMON
#define P_FAMILY_SNORLAX                 P_GEN_1_POKEMON
#define P_FAMILY_ARTICUNO                P_GEN_1_POKEMON
#define P_FAMILY_ZAPDOS                  P_GEN_1_POKEMON
#define P_FAMILY_MOLTRES                 P_GEN_1_POKEMON
#define P_FAMILY_DRATINI                 P_GEN_1_POKEMON
#define P_FAMILY_MEWTWO                  P_GEN_1_POKEMON
#define P_FAMILY_MEW                     P_GEN_1_POKEMON

#define P_FAMILY_CHIKORITA               P_GEN_2_POKEMON
#define P_FAMILY_CYNDAQUIL               P_GEN_2_POKEMON
#define P_FAMILY_TOTODILE                P_GEN_2_POKEMON
#define P_FAMILY_SENTRET                 P_GEN_2_POKEMON
#define P_FAMILY_HOOTHOOT                P_GEN_2_POKEMON
#define P_FAMILY_LEDYBA                  P_GEN_2_POKEMON
#define P_FAMILY_SPINARAK                P_GEN_2_POKEMON
#define P_FAMILY_CHINCHOU                P_GEN_2_POKEMON
#define P_FAMILY_TOGEPI                  P_GEN_2_POKEMON
#define P_FAMILY_NATU                    P_GEN_2_POKEMON
#define P_FAMILY_MAREEP                  P_GEN_2_POKEMON
#define P_FAMILY_MARILL                  P_GEN_2_POKEMON
#define P_FAMILY_SUDOWOODO               P_GEN_2_POKEMON
#define P_FAMILY_HOPPIP                  P_GEN_2_POKEMON
#define P_FAMILY_AIPOM                   P_GEN_2_POKEMON
#define P_FAMILY_SUNKERN                 P_GEN_2_POKEMON
#define P_FAMILY_YANMA                   P_GEN_2_POKEMON
#define P_FAMILY_WOOPER                  P_GEN_2_POKEMON
#define P_FAMILY_MURKROW                 P_GEN_2_POKEMON
#define P_FAMILY_MISDREAVUS              P_GEN_2_POKEMON
#define P_FAMILY_UNOWN                   P_GEN_2_POKEMON
#define P_FAMILY_WOBBUFFET               P_GEN_2_POKEMON
#define P_FAMILY_GIRAFARIG               P_GEN_2_POKEMON
#define P_FAMILY_PINECO                  P_GEN_2_POKEMON
#define P_FAMILY_DUNSPARCE               P_GEN_2_POKEMON
#define P_FAMILY_GLIGAR                  P_GEN_2_POKEMON
#define P_FAMILY_SNUBBULL                P_GEN_2_POKEMON
#define P_FAMILY_QWILFISH                P_GEN_2_POKEMON
#define P_FAMILY_SHUCKLE                 P_GEN_2_POKEMON
#define P_FAMILY_HERACROSS               P_GEN_2_POKEMON
#define P_FAMILY_SNEASEL                 P_GEN_2_POKEMON
#define P_FAMILY_TEDDIURSA               P_GEN_2_POKEMON
#define P_FAMILY_SLUGMA                  P_GEN_2_POKEMON
#define P_FAMILY_SWINUB                  P_GEN_2_POKEMON
#define P_FAMILY_CORSOLA                 P_GEN_2_POKEMON
#define P_FAMILY_REMORAID                P_GEN_2_POKEMON
#define P_FAMILY_DELIBIRD                P_GEN_2_POKEMON
#define P_FAMILY_MANTINE                 P_GEN_2_POKEMON
#define P_FAMILY_SKARMORY                P_GEN_2_POKEMON
#define P_FAMILY_HOUNDOUR                P_GEN_2_POKEMON
#define P_FAMILY_PHANPY                  P_GEN_2_POKEMON
#define P_FAMILY_STANTLER                P_GEN_2_POKEMON
#define P_FAMILY_SMEARGLE                P_GEN_2_POKEMON
#define P_FAMILY_MILTANK                 P_GEN_2_POKEMON
#define P_FAMILY_RAIKOU                  P_GEN_2_POKEMON
#define P_FAMILY_ENTEI                   P_GEN_2_POKEMON
#define P_FAMILY_SUICUNE                 P_GEN_2_POKEMON
#define P_FAMILY_LARVITAR                P_GEN_2_POKEMON
#define P_FAMILY_LUGIA                   P_GEN_2_POKEMON
#define P_FAMILY_HO_OH                   P_GEN_2_POKEMON
#define P_FAMILY_CELEBI                  P_GEN_2_POKEMON

#define P_FAMILY_TREECKO                 P_GEN_3_POKEMON
#define P_FAMILY_TORCHIC                 P_GEN_3_POKEMON
#define P_FAMILY_MUDKIP                  P_GEN_3_POKEMON
#define P_FAMILY_POOCHYENA               P_GEN_3_POKEMON
#define P_FAMILY_ZIGZAGOON               P_GEN_3_POKEMON
#define P_FAMILY_WURMPLE                 P_GEN_3_POKEMON
#define P_FAMILY_LOTAD                   P_GEN_3_POKEMON
#define P_FAMILY_SEEDOT                  P_GEN_3_POKEMON
#define P_FAMILY_TAILLOW                 P_GEN_3_POKEMON
#define P_FAMILY_WINGULL                 P_GEN_3_POKEMON
#define P_FAMILY_RALTS                   P_GEN_3_POKEMON
#define P_FAMILY_SURSKIT                 P_GEN_3_POKEMON
#define P_FAMILY_SHROOMISH               P_GEN_3_POKEMON
#define P_FAMILY_SLAKOTH                 P_GEN_3_POKEMON
#define P_FAMILY_NINCADA                 P_GEN_3_POKEMON
#define P_FAMILY_WHISMUR                 P_GEN_3_POKEMON
#define P_FAMILY_MAKUHITA                P_GEN_3_POKEMON
#define P_FAMILY_NOSEPASS                P_GEN_3_POKEMON
#define P_FAMILY_SKITTY                  P_GEN_3_POKEMON
#define P_FAMILY_SABLEYE                 P_GEN_3_POKEMON
#define P_FAMILY_MAWILE                  P_GEN_3_POKEMON
#define P_FAMILY_ARON                    P_GEN_3_POKEMON
#define P_FAMILY_MEDITITE                P_GEN_3_POKEMON
#define P_FAMILY_ELECTRIKE               P_GEN_3_POKEMON
#define P_FAMILY_PLUSLE                  P_GEN_3_POKEMON
#define P_FAMILY_MINUN                   P_GEN_3_POKEMON
#define P_FAMILY_VOLBEAT_ILLUMISE        P_GEN_3_POKEMON
#define P_FAMILY_ROSELIA                 P_GEN_3_POKEMON
#define P_FAMILY_GULPIN                  P_GEN_3_POKEMON
#define P_FAMILY_CARVANHA                P_GEN_3_POKEMON
#define P_FAMILY_WAILMER                 P_GEN_3_POKEMON
#define P_FAMILY_NUMEL                   P_GEN_3_POKEMON
#define P_FAMILY_TORKOAL                 P_GEN_3_POKEMON
#define P_FAMILY_SPOINK                  P_GEN_3_POKEMON
#define P_FAMILY_SPINDA                  P_GEN_3_POKEMON
#define P_FAMILY_TRAPINCH                P_GEN_3_POKEMON
#define P_FAMILY_CACNEA                  P_GEN_3_POKEMON
#define P_FAMILY_SWABLU                  P_GEN_3_POKEMON
#define P_FAMILY_ZANGOOSE                P_GEN_3_POKEMON
#define P_FAMILY_SEVIPER                 P_GEN_3_POKEMON
#define P_FAMILY_LUNATONE                P_GEN_3_POKEMON
#define P_FAMILY_SOLROCK                 P_GEN_3_POKEMON
#define P_FAMILY_BARBOACH                P_GEN_3_POKEMON
#define P_FAMILY_CORPHISH                P_GEN_3_POKEMON
#define P_FAMILY_BALTOY                  P_GEN_3_POKEMON
#define P_FAMILY_LILEEP                  P_GEN_3_POKEMON
#define P_FAMILY_ANORITH                 P_GEN_3_POKEMON
#define P_FAMILY_FEEBAS                  P_GEN_3_POKEMON
#define P_FAMILY_CASTFORM                P_GEN_3_POKEMON
#define P_FAMILY_KECLEON                 P_GEN_3_POKEMON
#define P_FAMILY_SHUPPET                 P_GEN_3_POKEMON
#define P_FAMILY_DUSKULL                 P_GEN_3_POKEMON
#define P_FAMILY_TROPIUS                 P_GEN_3_POKEMON
#define P_FAMILY_CHIMECHO                P_GEN_3_POKEMON
#define P_FAMILY_ABSOL                   P_GEN_3_POKEMON
#define P_FAMILY_SNORUNT                 P_GEN_3_POKEMON
#define P_FAMILY_SPHEAL                  P_GEN_3_POKEMON
#define P_FAMILY_CLAMPERL                P_GEN_3_POKEMON
#define P_FAMILY_RELICANTH               P_GEN_3_POKEMON
#define P_FAMILY_LUVDISC                 P_GEN_3_POKEMON
#define P_FAMILY_BAGON                   P_GEN_3_POKEMON
#define P_FAMILY_BELDUM                  P_GEN_3_POKEMON
#define P_FAMILY_REGIROCK                P_GEN_3_POKEMON
#define P_FAMILY_REGICE                  P_GEN_3_POKEMON
#define P_FAMILY_REGISTEEL               P_GEN_3_POKEMON
#define P_FAMILY_LATIAS                  P_GEN_3_POKEMON
#define P_FAMILY_LATIOS                  P_GEN_3_POKEMON
#define P_FAMILY_KYOGRE                  P_GEN_3_POKEMON
#define P_FAMILY_GROUDON                 P_GEN_3_POKEMON
#define P_FAMILY_RAYQUAZA                P_GEN_3_POKEMON
#define P_FAMILY_JIRACHI                 P_GEN_3_POKEMON
#define P_FAMILY_DEOXYS                  P_GEN_3_POKEMON

#define P_FAMILY_TURTWIG                 P_GEN_4_POKEMON
#define P_FAMILY_CHIMCHAR                P_GEN_4_POKEMON
#define P_FAMILY_PIPLUP                  P_GEN_4_POKEMON
#define P_FAMILY_STARLY                  P_GEN_4_POKEMON
#define P_FAMILY_BIDOOF                  P_GEN_4_POKEMON
#define P_FAMILY_KRICKETOT               P_GEN_4_POKEMON
#define P_FAMILY_SHINX                   P_GEN_4_POKEMON
#define P_FAMILY_CRANIDOS                P_GEN_4_POKEMON
#define P_FAMILY_SHIELDON                P_GEN_4_POKEMON
#define P_FAMILY_BURMY                   P_GEN_4_POKEMON
#define P_FAMILY_COMBEE                  P_GEN_4_POKEMON
#define P_FAMILY_PACHIRISU               P_GEN_4_POKEMON
#define P_FAMILY_BUIZEL                  P_GEN_4_POKEMON
#define P_FAMILY_CHERUBI                 P_GEN_4_POKEMON
#define P_FAMILY_SHELLOS                 P_GEN_4_POKEMON
#define P_FAMILY_DRIFLOON                P_GEN_4_POKEMON
#define P_FAMILY_BUNEARY                 P_GEN_4_POKEMON
#define P_FAMILY_GLAMEOW                 P_GEN_4_POKEMON
#define P_FAMILY_STUNKY                  P_GEN_4_POKEMON
#define P_FAMILY_BRONZOR                 P_GEN_4_POKEMON
#define P_FAMILY_CHATOT                  P_GEN_4_POKEMON
#define P_FAMILY_SPIRITOMB               P_GEN_4_POKEMON
#define P_FAMILY_GIBLE                   P_GEN_4_POKEMON
#define P_FAMILY_RIOLU                   P_GEN_4_POKEMON
#define P_FAMILY_HIPPOPOTAS              P_GEN_4_POKEMON
#define P_FAMILY_SKORUPI                 P_GEN_4_POKEMON
#define P_FAMILY_CROAGUNK                P_GEN_4_POKEMON
#define P_FAMILY_CARNIVINE               P_GEN_4_POKEMON
#define P_FAMILY_FINNEON                 P_GEN_4_POKEMON
#define P_FAMILY_SNOVER                  P_GEN_4_POKEMON
#define P_FAMILY_ROTOM                   P_GEN_4_POKEMON
#define P_FAMILY_UXIE                    P_GEN_4_POKEMON
#define P_FAMILY_MESPRIT                 P_GEN_4_POKEMON
#define P_FAMILY_AZELF                   P_GEN_4_POKEMON
#define P_FAMILY_DIALGA                  P_GEN_4_POKEMON
#define P_FAMILY_PALKIA                  P_GEN_4_POKEMON
#define P_FAMILY_HEATRAN                 P_GEN_4_POKEMON
#define P_FAMILY_REGIGIGAS               P_GEN_4_POKEMON
#define P_FAMILY_GIRATINA                P_GEN_4_POKEMON
#define P_FAMILY_CRESSELIA               P_GEN_4_POKEMON
#define P_FAMILY_MANAPHY                 P_GEN_4_POKEMON
#define P_FAMILY_DARKRAI                 P_GEN_4_POKEMON
#define P_FAMILY_SHAYMIN                 P_GEN_4_POKEMON
#define P_FAMILY_ARCEUS                  P_GEN_4_POKEMON

#define P_FAMILY_VICTINI                 FALSE // TREY: not in roster
#define P_FAMILY_SNIVY                   FALSE // TREY: not in roster
#define P_FAMILY_TEPIG                   FALSE // TREY: not in roster
#define P_FAMILY_OSHAWOTT                FALSE // TREY: not in roster
#define P_FAMILY_PATRAT                  FALSE // TREY: not in roster
#define P_FAMILY_LILLIPUP                FALSE // TREY: not in roster
#define P_FAMILY_PURRLOIN                FALSE // TREY: not in roster
#define P_FAMILY_PANSAGE                 FALSE // TREY: not in roster
#define P_FAMILY_PANSEAR                 FALSE // TREY: not in roster
#define P_FAMILY_PANPOUR                 FALSE // TREY: not in roster
#define P_FAMILY_MUNNA                   FALSE // TREY: not in roster
#define P_FAMILY_PIDOVE                  FALSE // TREY: not in roster
#define P_FAMILY_BLITZLE                 FALSE // TREY: not in roster
#define P_FAMILY_ROGGENROLA              FALSE // TREY: not in roster
#define P_FAMILY_WOOBAT                  FALSE // TREY: not in roster
#define P_FAMILY_DRILBUR                 FALSE // TREY: not in roster
#define P_FAMILY_AUDINO                  FALSE // TREY: not in roster
#define P_FAMILY_TIMBURR                 TRUE  // TREY roster: Kitakami
#define P_FAMILY_TYMPOLE                 FALSE // TREY: not in roster
#define P_FAMILY_THROH                   FALSE // TREY: not in roster
#define P_FAMILY_SAWK                    FALSE // TREY: not in roster
#define P_FAMILY_SEWADDLE                TRUE  // TREY roster: Kitakami
#define P_FAMILY_VENIPEDE                FALSE // TREY: not in roster
#define P_FAMILY_COTTONEE                FALSE // TREY: not in roster
#define P_FAMILY_PETILIL                 TRUE  // TREY roster: Kitakami
#define P_FAMILY_BASCULIN                TRUE  // TREY roster: Kitakami
#define P_FAMILY_SANDILE                 FALSE // TREY: not in roster
#define P_FAMILY_DARUMAKA                FALSE // TREY: not in roster
#define P_FAMILY_MARACTUS                FALSE // TREY: not in roster
#define P_FAMILY_DWEBBLE                 FALSE // TREY: not in roster
#define P_FAMILY_SCRAGGY                 FALSE // TREY: not in roster
#define P_FAMILY_SIGILYPH                FALSE // TREY: not in roster
#define P_FAMILY_YAMASK                  FALSE // TREY: not in roster
#define P_FAMILY_TIRTOUGA                FALSE // TREY: not in roster
#define P_FAMILY_ARCHEN                  FALSE // TREY: not in roster
#define P_FAMILY_TRUBBISH                FALSE // TREY: not in roster
#define P_FAMILY_ZORUA                   FALSE // TREY: not in roster
#define P_FAMILY_MINCCINO                FALSE // TREY: not in roster
#define P_FAMILY_GOTHITA                 FALSE // TREY: not in roster
#define P_FAMILY_SOLOSIS                 FALSE // TREY: not in roster
#define P_FAMILY_DUCKLETT                TRUE  // TREY roster: Kitakami
#define P_FAMILY_VANILLITE               FALSE // TREY: not in roster
#define P_FAMILY_DEERLING                FALSE // TREY: not in roster
#define P_FAMILY_EMOLGA                  FALSE // TREY: not in roster
#define P_FAMILY_KARRABLAST              FALSE // TREY: not in roster
#define P_FAMILY_FOONGUS                 FALSE // TREY: not in roster
#define P_FAMILY_FRILLISH                FALSE // TREY: not in roster
#define P_FAMILY_ALOMOMOLA               FALSE // TREY: not in roster
#define P_FAMILY_JOLTIK                  FALSE // TREY: not in roster
#define P_FAMILY_FERROSEED               FALSE // TREY: not in roster
#define P_FAMILY_KLINK                   FALSE // TREY: not in roster
#define P_FAMILY_TYNAMO                  TRUE  // TREY roster: Kitakami
#define P_FAMILY_ELGYEM                  FALSE // TREY: not in roster
#define P_FAMILY_LITWICK                 TRUE  // TREY roster: Kitakami
#define P_FAMILY_AXEW                    FALSE // TREY: not in roster
#define P_FAMILY_CUBCHOO                 FALSE // TREY: not in roster
#define P_FAMILY_CRYOGONAL               FALSE // TREY: not in roster
#define P_FAMILY_SHELMET                 FALSE // TREY: not in roster
#define P_FAMILY_STUNFISK                FALSE // TREY: not in roster
#define P_FAMILY_MIENFOO                 TRUE  // TREY roster: Kitakami
#define P_FAMILY_DRUDDIGON               FALSE // TREY: not in roster
#define P_FAMILY_GOLETT                  FALSE // TREY: not in roster
#define P_FAMILY_PAWNIARD                TRUE  // TREY roster: Kitakami
#define P_FAMILY_BOUFFALANT              FALSE // TREY: not in roster
#define P_FAMILY_RUFFLET                 FALSE // TREY: not in roster
#define P_FAMILY_VULLABY                 TRUE  // TREY roster: Kitakami
#define P_FAMILY_HEATMOR                 FALSE // TREY: not in roster
#define P_FAMILY_DURANT                  FALSE // TREY: not in roster
#define P_FAMILY_DEINO                   FALSE // TREY: not in roster
#define P_FAMILY_LARVESTA                FALSE // TREY: not in roster
#define P_FAMILY_COBALION                FALSE // TREY: not in roster
#define P_FAMILY_TERRAKION               FALSE // TREY: not in roster
#define P_FAMILY_VIRIZION                FALSE // TREY: not in roster
#define P_FAMILY_TORNADUS                FALSE // TREY: not in roster
#define P_FAMILY_THUNDURUS               FALSE // TREY: not in roster
#define P_FAMILY_RESHIRAM                FALSE // TREY: not in roster
#define P_FAMILY_ZEKROM                  FALSE // TREY: not in roster
#define P_FAMILY_LANDORUS                FALSE // TREY: not in roster
#define P_FAMILY_KYUREM                  FALSE // TREY: not in roster
#define P_FAMILY_KELDEO                  FALSE // TREY: not in roster
#define P_FAMILY_MELOETTA                FALSE // TREY: not in roster
#define P_FAMILY_GENESECT                FALSE // TREY: not in roster

#define P_FAMILY_CHESPIN                 FALSE // TREY: not in roster
#define P_FAMILY_FENNEKIN                FALSE // TREY: not in roster
#define P_FAMILY_FROAKIE                 FALSE // TREY: not in roster
#define P_FAMILY_BUNNELBY                FALSE // TREY: not in roster
#define P_FAMILY_FLETCHLING              FALSE // TREY: not in roster
#define P_FAMILY_SCATTERBUG              FALSE // TREY: not in roster
#define P_FAMILY_LITLEO                  FALSE // TREY: not in roster
#define P_FAMILY_FLABEBE                 FALSE // TREY: not in roster
#define P_FAMILY_SKIDDO                  FALSE // TREY: not in roster
#define P_FAMILY_PANCHAM                 FALSE // TREY: not in roster
#define P_FAMILY_FURFROU                 FALSE // TREY: not in roster
#define P_FAMILY_ESPURR                  FALSE // TREY: not in roster
#define P_FAMILY_HONEDGE                 FALSE // TREY: not in roster
#define P_FAMILY_SPRITZEE                FALSE // TREY: not in roster
#define P_FAMILY_SWIRLIX                 FALSE // TREY: not in roster
#define P_FAMILY_INKAY                   FALSE // TREY: not in roster
#define P_FAMILY_BINACLE                 FALSE // TREY: not in roster
#define P_FAMILY_SKRELP                  FALSE // TREY: not in roster
#define P_FAMILY_CLAUNCHER               FALSE // TREY: not in roster
#define P_FAMILY_HELIOPTILE              FALSE // TREY: not in roster
#define P_FAMILY_TYRUNT                  FALSE // TREY: not in roster
#define P_FAMILY_AMAURA                  FALSE // TREY: not in roster
#define P_FAMILY_HAWLUCHA                FALSE // TREY: not in roster
#define P_FAMILY_DEDENNE                 FALSE // TREY: not in roster
#define P_FAMILY_CARBINK                 TRUE  // TREY roster: Kitakami
#define P_FAMILY_GOOMY                   TRUE  // TREY roster: Kitakami
#define P_FAMILY_KLEFKI                  FALSE // TREY: not in roster
#define P_FAMILY_PHANTUMP                TRUE  // TREY roster: Kitakami
#define P_FAMILY_PUMPKABOO               FALSE // TREY: not in roster
#define P_FAMILY_BERGMITE                FALSE // TREY: not in roster
#define P_FAMILY_NOIBAT                  TRUE  // TREY roster: Kitakami
#define P_FAMILY_XERNEAS                 FALSE // TREY: not in roster
#define P_FAMILY_YVELTAL                 FALSE // TREY: not in roster
#define P_FAMILY_ZYGARDE                 FALSE // TREY: not in roster
#define P_FAMILY_DIANCIE                 FALSE // TREY: not in roster
#define P_FAMILY_HOOPA                   FALSE // TREY: not in roster
#define P_FAMILY_VOLCANION               FALSE // TREY: not in roster

#define P_FAMILY_ROWLET                  FALSE // TREY: not in roster
#define P_FAMILY_LITTEN                  FALSE // TREY: not in roster
#define P_FAMILY_POPPLIO                 FALSE // TREY: not in roster
#define P_FAMILY_PIKIPEK                 FALSE // TREY: not in roster
#define P_FAMILY_YUNGOOS                 FALSE // TREY: not in roster
#define P_FAMILY_GRUBBIN                 TRUE  // TREY roster: Kitakami
#define P_FAMILY_CRABRAWLER              FALSE // TREY: not in roster
#define P_FAMILY_ORICORIO                TRUE  // TREY roster: Kitakami
#define P_FAMILY_CUTIEFLY                TRUE  // TREY roster: Kitakami
#define P_FAMILY_ROCKRUFF                TRUE  // TREY roster: Kitakami
#define P_FAMILY_WISHIWASHI              FALSE // TREY: not in roster
#define P_FAMILY_MAREANIE                FALSE // TREY: not in roster
#define P_FAMILY_MUDBRAY                 TRUE  // TREY roster: Kitakami
#define P_FAMILY_DEWPIDER                FALSE // TREY: not in roster
#define P_FAMILY_FOMANTIS                TRUE  // TREY roster: Kitakami
#define P_FAMILY_MORELULL                FALSE // TREY: not in roster
#define P_FAMILY_SALANDIT                TRUE  // TREY roster: Kitakami
#define P_FAMILY_STUFFUL                 FALSE // TREY: not in roster
#define P_FAMILY_BOUNSWEET               FALSE // TREY: not in roster
#define P_FAMILY_COMFEY                  FALSE // TREY: not in roster
#define P_FAMILY_ORANGURU                FALSE // TREY: not in roster
#define P_FAMILY_PASSIMIAN               FALSE // TREY: not in roster
#define P_FAMILY_WIMPOD                  FALSE // TREY: not in roster
#define P_FAMILY_SANDYGAST               FALSE // TREY: not in roster
#define P_FAMILY_PYUKUMUKU               FALSE // TREY: not in roster
#define P_FAMILY_TYPE_NULL               FALSE // TREY: not in roster
#define P_FAMILY_MINIOR                  FALSE // TREY: not in roster
#define P_FAMILY_KOMALA                  FALSE // TREY: not in roster
#define P_FAMILY_TURTONATOR              FALSE // TREY: not in roster
#define P_FAMILY_TOGEDEMARU              FALSE // TREY: not in roster
#define P_FAMILY_MIMIKYU                 TRUE  // TREY roster: Kitakami
#define P_FAMILY_BRUXISH                 FALSE // TREY: not in roster
#define P_FAMILY_DRAMPA                  FALSE // TREY: not in roster
#define P_FAMILY_DHELMISE                FALSE // TREY: not in roster
#define P_FAMILY_JANGMO_O                TRUE  // TREY roster: Kitakami
#define P_FAMILY_TAPU_KOKO               FALSE // TREY: not in roster
#define P_FAMILY_TAPU_LELE               FALSE // TREY: not in roster
#define P_FAMILY_TAPU_BULU               FALSE // TREY: not in roster
#define P_FAMILY_TAPU_FINI               FALSE // TREY: not in roster
#define P_FAMILY_COSMOG                  FALSE // TREY: not in roster
#define P_FAMILY_NIHILEGO                FALSE // TREY: not in roster
#define P_FAMILY_BUZZWOLE                FALSE // TREY: not in roster
#define P_FAMILY_PHEROMOSA               FALSE // TREY: not in roster
#define P_FAMILY_XURKITREE               FALSE // TREY: not in roster
#define P_FAMILY_CELESTEELA              FALSE // TREY: not in roster
#define P_FAMILY_KARTANA                 FALSE // TREY: not in roster
#define P_FAMILY_GUZZLORD                FALSE // TREY: not in roster
#define P_FAMILY_NECROZMA                FALSE // TREY: not in roster
#define P_FAMILY_MAGEARNA                FALSE // TREY: not in roster
#define P_FAMILY_MARSHADOW               FALSE // TREY: not in roster
#define P_FAMILY_POIPOLE                 FALSE // TREY: not in roster
#define P_FAMILY_STAKATAKA               FALSE // TREY: not in roster
#define P_FAMILY_BLACEPHALON             FALSE // TREY: not in roster
#define P_FAMILY_ZERAORA                 FALSE // TREY: not in roster
#define P_FAMILY_MELTAN                  FALSE // TREY: not in roster

#define P_FAMILY_GROOKEY                 FALSE // TREY: not in roster
#define P_FAMILY_SCORBUNNY               FALSE // TREY: not in roster
#define P_FAMILY_SOBBLE                  FALSE // TREY: not in roster
#define P_FAMILY_SKWOVET                 TRUE  // TREY roster: Kitakami
#define P_FAMILY_ROOKIDEE                FALSE // TREY: not in roster
#define P_FAMILY_BLIPBUG                 FALSE // TREY: not in roster
#define P_FAMILY_NICKIT                  FALSE // TREY: not in roster
#define P_FAMILY_GOSSIFLEUR              FALSE // TREY: not in roster
#define P_FAMILY_WOOLOO                  FALSE // TREY: not in roster
#define P_FAMILY_CHEWTLE                 TRUE  // TREY roster: Kitakami
#define P_FAMILY_YAMPER                  FALSE // TREY: not in roster
#define P_FAMILY_ROLYCOLY                FALSE // TREY: not in roster
#define P_FAMILY_APPLIN                  TRUE  // TREY roster: Kitakami
#define P_FAMILY_SILICOBRA               FALSE // TREY: not in roster
#define P_FAMILY_CRAMORANT               TRUE  // TREY roster: Kitakami
#define P_FAMILY_ARROKUDA                TRUE  // TREY roster: Kitakami
#define P_FAMILY_TOXEL                   FALSE // TREY: not in roster
#define P_FAMILY_SIZZLIPEDE              FALSE // TREY: not in roster
#define P_FAMILY_CLOBBOPUS               FALSE // TREY: not in roster
#define P_FAMILY_SINISTEA                FALSE // TREY: not in roster
#define P_FAMILY_HATENNA                 TRUE  // TREY roster: Kitakami
#define P_FAMILY_IMPIDIMP                TRUE  // TREY roster: Kitakami
#define P_FAMILY_MILCERY                 FALSE // TREY: not in roster
#define P_FAMILY_FALINKS                 FALSE // TREY: not in roster
#define P_FAMILY_PINCURCHIN              FALSE // TREY: not in roster
#define P_FAMILY_SNOM                    FALSE // TREY: not in roster
#define P_FAMILY_STONJOURNER             FALSE // TREY: not in roster
#define P_FAMILY_EISCUE                  FALSE // TREY: not in roster
#define P_FAMILY_INDEEDEE                TRUE  // TREY roster: Kitakami
#define P_FAMILY_MORPEKO                 TRUE  // TREY roster: Kitakami
#define P_FAMILY_CUFANT                  FALSE // TREY: not in roster
#define P_FAMILY_DRACOZOLT               FALSE // TREY: not in roster
#define P_FAMILY_ARCTOZOLT               FALSE // TREY: not in roster
#define P_FAMILY_DRACOVISH               FALSE // TREY: not in roster
#define P_FAMILY_ARCTOVISH               FALSE // TREY: not in roster
#define P_FAMILY_DURALUDON               FALSE // TREY: not in roster
#define P_FAMILY_DREEPY                  FALSE // TREY: not in roster
#define P_FAMILY_ZACIAN                  FALSE // TREY: not in roster
#define P_FAMILY_ZAMAZENTA               FALSE // TREY: not in roster
#define P_FAMILY_ETERNATUS               FALSE // TREY: not in roster
#define P_FAMILY_KUBFU                   FALSE // TREY: not in roster
#define P_FAMILY_ZARUDE                  FALSE // TREY: not in roster
#define P_FAMILY_REGIELEKI               FALSE // TREY: not in roster
#define P_FAMILY_REGIDRAGO               FALSE // TREY: not in roster
#define P_FAMILY_GLASTRIER               FALSE // TREY: not in roster
#define P_FAMILY_SPECTRIER               FALSE // TREY: not in roster
#define P_FAMILY_CALYREX                 FALSE // TREY: not in roster
#define P_FAMILY_ENAMORUS                FALSE // TREY: not in roster

#define P_FAMILY_SPRIGATITO              FALSE // TREY: not in roster
#define P_FAMILY_FUECOCO                 FALSE // TREY: not in roster
#define P_FAMILY_QUAXLY                  FALSE // TREY: not in roster
#define P_FAMILY_LECHONK                 FALSE // TREY: not in roster
#define P_FAMILY_TAROUNTULA              FALSE // TREY: not in roster
#define P_FAMILY_NYMBLE                  FALSE // TREY: not in roster
#define P_FAMILY_PAWMI                   FALSE // TREY: not in roster
#define P_FAMILY_TANDEMAUS               TRUE  // TREY roster: Kitakami
#define P_FAMILY_FIDOUGH                 FALSE // TREY: not in roster
#define P_FAMILY_SMOLIV                  FALSE // TREY: not in roster
#define P_FAMILY_SQUAWKABILLY            FALSE // TREY: not in roster
#define P_FAMILY_NACLI                   FALSE // TREY: not in roster
#define P_FAMILY_CHARCADET               FALSE // TREY: not in roster
#define P_FAMILY_TADBULB                 FALSE // TREY: not in roster
#define P_FAMILY_WATTREL                 FALSE // TREY: not in roster
#define P_FAMILY_MASCHIFF                FALSE // TREY: not in roster
#define P_FAMILY_SHROODLE                FALSE // TREY: not in roster
#define P_FAMILY_BRAMBLIN                FALSE // TREY: not in roster
#define P_FAMILY_TOEDSCOOL               TRUE  // TREY roster: Kitakami
#define P_FAMILY_KLAWF                   FALSE // TREY: not in roster
#define P_FAMILY_CAPSAKID                FALSE // TREY: not in roster
#define P_FAMILY_RELLOR                  FALSE // TREY: not in roster
#define P_FAMILY_FLITTLE                 FALSE // TREY: not in roster
#define P_FAMILY_TINKATINK               FALSE // TREY: not in roster
#define P_FAMILY_WIGLETT                 FALSE // TREY: not in roster
#define P_FAMILY_BOMBIRDIER              TRUE  // TREY roster: Kitakami
#define P_FAMILY_FINIZEN                 FALSE // TREY: not in roster
#define P_FAMILY_VAROOM                  FALSE // TREY: not in roster
#define P_FAMILY_CYCLIZAR                FALSE // TREY: not in roster
#define P_FAMILY_ORTHWORM                TRUE  // TREY roster: Kitakami
#define P_FAMILY_GLIMMET                 TRUE  // TREY roster: Kitakami
#define P_FAMILY_GREAVARD                FALSE // TREY: not in roster
#define P_FAMILY_FLAMIGO                 FALSE // TREY: not in roster
#define P_FAMILY_CETODDLE                FALSE // TREY: not in roster
#define P_FAMILY_VELUZA                  FALSE // TREY: not in roster
#define P_FAMILY_DONDOZO                 FALSE // TREY: not in roster
#define P_FAMILY_TATSUGIRI               FALSE // TREY: not in roster
#define P_FAMILY_GREAT_TUSK              FALSE // TREY: not in roster
#define P_FAMILY_SCREAM_TAIL             FALSE // TREY: not in roster
#define P_FAMILY_BRUTE_BONNET            FALSE // TREY: not in roster
#define P_FAMILY_FLUTTER_MANE            FALSE // TREY: not in roster
#define P_FAMILY_SLITHER_WING            FALSE // TREY: not in roster
#define P_FAMILY_SANDY_SHOCKS            FALSE // TREY: not in roster
#define P_FAMILY_IRON_TREADS             FALSE // TREY: not in roster
#define P_FAMILY_IRON_BUNDLE             FALSE // TREY: not in roster
#define P_FAMILY_IRON_HANDS              FALSE // TREY: not in roster
#define P_FAMILY_IRON_JUGULIS            FALSE // TREY: not in roster
#define P_FAMILY_IRON_MOTH               FALSE // TREY: not in roster
#define P_FAMILY_IRON_THORNS             FALSE // TREY: not in roster
#define P_FAMILY_FRIGIBAX                FALSE // TREY: not in roster
#define P_FAMILY_GIMMIGHOUL              FALSE // TREY: not in roster
#define P_FAMILY_WO_CHIEN                FALSE // TREY: not in roster
#define P_FAMILY_CHIEN_PAO               FALSE // TREY: not in roster
#define P_FAMILY_TING_LU                 FALSE // TREY: not in roster
#define P_FAMILY_CHI_YU                  FALSE // TREY: not in roster
#define P_FAMILY_ROARING_MOON            FALSE // TREY: not in roster
#define P_FAMILY_IRON_VALIANT            FALSE // TREY: not in roster
#define P_FAMILY_KORAIDON                FALSE // TREY: not in roster
#define P_FAMILY_MIRAIDON                FALSE // TREY: not in roster
#define P_FAMILY_WALKING_WAKE            FALSE // TREY: not in roster
#define P_FAMILY_IRON_LEAVES             FALSE // TREY: not in roster
#define P_FAMILY_POLTCHAGEIST            TRUE  // TREY roster: Kitakami
#define P_FAMILY_SINISTCHA               FALSE // TREY: not in roster
#define P_FAMILY_OKIDOGI                 TRUE  // TREY roster: Kitakami
#define P_FAMILY_MUNKIDORI               TRUE  // TREY roster: Kitakami
#define P_FAMILY_FEZANDIPITI             TRUE  // TREY roster: Kitakami
#define P_FAMILY_OGERPON                 TRUE  // TREY roster: Kitakami
#define P_FAMILY_GOUGING_FIRE            FALSE // TREY: not in roster
#define P_FAMILY_RAGING_BOLT             FALSE // TREY: not in roster
#define P_FAMILY_IRON_BOULDER            FALSE // TREY: not in roster
#define P_FAMILY_IRON_CROWN              FALSE // TREY: not in roster
#define P_FAMILY_TERAPAGOS               FALSE // TREY: not in roster
#define P_FAMILY_PECHARUNT               FALSE // TREY: not in roster

#endif // GUARD_CONFIG_SPECIES_ENABLED_H
