# coding=utf-8

TEMPLATE_CONTEXTS = {
    "core": {
        "resolution": (1920, 1080),
        "needs_scaling": False,
        "hub_count": 8,  # Default number of hub rows on home screen
        "search_hub_count": 12,  # Fixed search result rows; must match SearchWindow.SEARCH_HUB_COUNT
    },
    "indicators": {
        "base": {
            "show": True
        },
        "none": {
            "INHERIT": "base",
            "use_unwatched": True,
            "show": False
        },
        "modern": {
            "INHERIT": "base",
            "use_unwatched": False,
            "hide_aw_bg": False,
            "watched_bg": "CC000000",
            "unwatched_count_bg": "CC000000",
            "textcolor": "FFFFFFFF",
            "assets": {
                "watched": "watched.png"
            }
        },
        "modern_2024": {
            "INHERIT": "modern",
            "assets": {
                "watched": "watched_2024.png"
            }
        }
    },
    "themes": {
        "base": {
            # general config
            "assets": {
                "buttons": {
                    "base": "script.plex/buttons/",
                    "focusSuffix": "-focus",
                }
            },
            "buttons": {
                "useFocusColor": True,
                "useNoFocusColor": True,
                "zoomPlayButton": False,
                "focusColor": None,
                "noFocusColor": None
            },

            # specific interface config; kept in lockstep with pre_play's button sizing/spacing below
            # since the episode/seasons row's play buttons are the same visual element on both screens
            "episodes": {
                "buttongroup": {
                    "itemgap": -20,
                },
                "buttons": {
                    "width": None,
                    "height": None,
                }
            },
            "seasons": {
                "buttongroup": {
                    "itemgap": -20
                },
                "buttons": {
                    "width": None,
                    "height": None,
                }
            },
            # ArtistWindow's own button row (script-plex-artist.xml.tpl) - retuned to match
            # episodes/seasons/pre_play above (same visual element, same reasoning).
            "artist": {
                "buttongroup": {
                    "itemgap": -20
                },
                "buttons": {
                    "width": None,
                    "height": None,
                }
            },
            "pre_play": {
                "buttongroup": {
                    "itemgap": -20
                },
                "buttons": {
                    "width": None,
                    "height": None,
                }
            },
            # library grid windows' own Play/Shuffle (script-plex-posters.xml.tpl etc.) - kept in
            # lockstep with episodes/seasons/pre_play above, same reasoning: same visual element.
            "library": {
                "buttongroup": {
                    "itemgap": -20
                },
                "buttons": {
                    "width": None,
                    "height": None,
                }
            },
            # The music player / current-playlist transport row (includes/music_player_buttons.xml.tpl)
            # - the row's own long-standing geometry, kept here so the base theme renders as before.
            "music_player": {
                "buttongroup": {
                    "itemgap": -40
                },
                "buttons": {
                    "width": 125,
                    "height": 101,
                },
                "buttons_hitrect": {
                    "x": 28,
                    "y": 28,
                    "w": 69,
                    "h": 45,
                }
            }
        },
        "modern": {
            "INHERIT": "base",
            "assets": {
                "buttons": {
                    "base": "script.plex/buttons/player/modern/",
                    "focusSuffix": "",
                }
            },
            "buttons": {
                "useFocusColor": False,
                "zoomPlayButton": True,
                "noFocusColor": "88FFFFFF"
            },
            # 70x70/itemgap 0, not 152x121/-60: the source icons (script.plex/buttons/player/modern/
            # *.png) used to carry a lot of dead transparent padding around each glyph on a shared
            # 180x145 canvas (union of every glyph's own opaque bbox across the whole icon set was
            # only 50x50, centered) - the old width/height/itemgap were all sized/tuned to compensate
            # for that padding (negative itemgap pulling the padded boxes back together so the
            # visible glyphs read at a sane distance apart). The icons were cropped to a shared, still
            # centered 80x80 canvas (~15px margin around the widest glyph) to remove most of that
            # dead space - width/height/itemgap below are re-tuned to match: 70x70 keeps roughly the
            # same on-screen glyph size as before while dropping the wasted canvas around it, and
            # itemgap 0 replaces the old negative-overlap compensation entirely (the tight boxes'
            # own margins already provide enough visual breathing room, no pull-together needed) -
            # this also leaves more room to add further buttons to the row later.
            # x=5,y=5,w=60,h=60: themed_button.xml.tpl's own hitrect default (40,40,96,60) was tuned
            # for the old 152x121 box and would extend well past this new 70x70 one (and, with
            # itemgap now 0, into the next button's own box) - passed explicitly per-window below
            # rather than changed globally in themed_button.xml.tpl, since that default is also
            # still used by every other themed_button.xml.tpl caller (library grid windows etc.)
            # whose own box sizes weren't touched here.
            "episodes": {
                "buttongroup": {
                    "itemgap": 0,
                },
                "buttons": {
                    "width": 70,
                    "height": 70,
                },
                "buttons_hitrect": {
                    "x": 5,
                    "y": 5,
                    "w": 60,
                    "h": 60,
                }
            },
            "seasons": {
                "buttongroup": {
                    "itemgap": 0
                },
                "buttons": {
                    "width": 70,
                    "height": 70,
                },
                "buttons_hitrect": {
                    "x": 5,
                    "y": 5,
                    "w": 60,
                    "h": 60,
                }
            },
            "artist": {
                "buttongroup": {
                    "itemgap": 0
                },
                "buttons": {
                    "width": 70,
                    "height": 70,
                },
                "buttons_hitrect": {
                    "x": 5,
                    "y": 5,
                    "w": 60,
                    "h": 60,
                }
            },
            "pre_play": {
                "buttongroup": {
                    "itemgap": 0
                },
                "buttons": {
                    "width": 70,
                    "height": 70,
                },
                "buttons_hitrect": {
                    "x": 5,
                    "y": 5,
                    "w": 60,
                    "h": 60,
                }
            },
            "library": {
                "buttongroup": {
                    "itemgap": 0
                },
                "buttons": {
                    "width": 70,
                    "height": 70,
                },
                "buttons_hitrect": {
                    "x": 5,
                    "y": 5,
                    "w": 60,
                    "h": 60,
                }
            },
            # music player / current-playlist transport row - same treatment as the rows above.
            "music_player": {
                "buttongroup": {
                    "itemgap": 0
                },
                "buttons": {
                    "width": 70,
                    "height": 70,
                },
                "buttons_hitrect": {
                    "x": 5,
                    "y": 5,
                    "w": 60,
                    "h": 60,
                }
            }
        },
        "modern-colored": {
            "INHERIT": "modern",
            "buttons": {
                "useFocusColor": True,
                "zoomPlayButton": False,
            }
        },
    }
}
