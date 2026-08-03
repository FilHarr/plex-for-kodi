# coding=utf-8

TEMPLATE_CONTEXTS = {
    "core": {
        "resolution": (1920, 1080),
        "needs_scaling": False,
        "hub_count": 8,  # Default number of hub rows on home screen
        "search_hub_count": 12,  # Fixed search result rows; must match SearchDialog.SEARCH_HUB_COUNT
    },
    "indicators": {
        "base": {
            "use_scaling": False,
            "show": True,
            "scale": {

            }
        },
        "none": {
            "INHERIT": "base",
            "use_unwatched": True,
            "show": False
        },
        "classic": {
            "INHERIT": "base",
            "use_unwatched": True,
            "hide_aw_bg": None,
            "watched_bg": None,
            "unwatched_count_bg": "FFCC7B19",
            "textcolor": "FF000000",
            "assets": {
                "unwatched": "unwatched.png"
            }
        },
        "modern": {
            "INHERIT": "base",
            "use_scaling": True,
            "scale": {
                "tiny": 0.75,
                "small": 1.0,
                "medium": 1.175,
                "large": 1.3
            },
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
            # since the episode row's play buttons are the same visual element on both screens
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
            "pre_play": {
                "buttongroup": {
                    "itemgap": -20
                },
                "buttons": {
                    "width": None,
                    "height": None,
                }
            }
        },
        "classic": {
            "INHERIT": "base",
            "episodes": {
                "buttongroup": {
                    "itemgap": -50
                },
                "buttons": {
                    "width": 176,
                    "height": 140
                }
            },
            "seasons": {
                "buttons": {
                    "width": 126,
                    "height": 100,
                }
            },
            "pre_play": {
                "buttongroup": {
                    "itemgap": -50
                },
                "buttons": {
                    "width": 176,
                    "height": 140,
                }
            },
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
            "episodes": {
                "buttongroup": {
                    "itemgap": -60,
                },
                "buttons": {
                    "width": 152,
                    "height": 121,
                }
            },
            "seasons": {
                "buttongroup": {
                    "itemgap": -40
                },
                "buttons": {
                    "width": 152,
                    "height": 121,
                }
            },
            "pre_play": {
                "buttongroup": {
                    "itemgap": -60
                },
                "buttons": {
                    "width": 152,
                    "height": 121,
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
        "modern-dotted": {
            "INHERIT": "modern",
            "assets": {
                "buttons": {
                    "base": "script.plex/buttons/player/modern-dotted/",
                    "focusSuffix": "-focus",
                }
            },
            "buttons": {
                "useFocusColor": False,
                "zoomPlayButton": False,
            }
        }
    }
}
