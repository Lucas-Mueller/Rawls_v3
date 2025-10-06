# Experiment Results JSON Schema

- Source file: `xperiment_data/experiment_results_20250811_134724.json`
- Schema type: JSON Schema Draft-07 (inferred)

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "Experiment Results Schema (inferred)",
  "type": "object",
  "properties": {
    "general_information": {
      "type": "object",
      "properties": {
        "consensus_reached": {
          "type": "boolean"
        },
        "consensus_principle": {
          "type": "null"
        },
        "public_conversation_phase_2": {
          "type": "string"
        },
        "final_vote_results": {
          "type": "object",
          "properties": {
            "Alice": {
              "type": "string"
            },
            "Bob": {
              "type": "string"
            },
            "Donald": {
              "type": "string"
            }
          },
          "required": [
            "Alice",
            "Bob",
            "Donald"
          ],
          "additionalProperties": false
        },
        "config_file_used": {
          "type": "string"
        }
      },
      "required": [
        "config_file_used",
        "consensus_principle",
        "consensus_reached",
        "final_vote_results",
        "public_conversation_phase_2"
      ],
      "additionalProperties": false
    },
    "agents": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "model": {
            "type": "string"
          },
          "name": {
            "type": "string"
          },
          "personality": {
            "type": "string"
          },
          "phase_1": {
            "type": "object",
            "properties": {
              "demonstrations": {
                "type": "array",
                "items": {
                  "type": "object",
                  "properties": {
                    "bank_balance_after_round": {
                      "type": "number"
                    },
                    "choice_principal": {
                      "type": "string"
                    },
                    "class_put_in": {
                      "type": "string"
                    },
                    "memory_coming_in_this_round": {
                      "type": "string"
                    },
                    "number_demonstration_round": {
                      "type": "integer"
                    },
                    "payoff_if_other_principles": {
                      "type": "string"
                    },
                    "payoff_received": {
                      "type": "number"
                    }
                  },
                  "required": [
                    "bank_balance_after_round",
                    "choice_principal",
                    "class_put_in",
                    "memory_coming_in_this_round",
                    "number_demonstration_round",
                    "payoff_if_other_principles",
                    "payoff_received"
                  ],
                  "additionalProperties": false
                }
              },
              "detailed_explanation": {
                "type": "object",
                "properties": {
                  "memory_coming_in_this_round": {
                    "type": "string"
                  },
                  "response_to_demonstration": {
                    "type": "string"
                  }
                },
                "required": [
                  "memory_coming_in_this_round",
                  "response_to_demonstration"
                ],
                "additionalProperties": false
              },
              "initial_ranking": {
                "type": "object",
                "properties": {
                  "bank_balance": {
                    "type": "number"
                  },
                  "memory_coming_in_this_round": {
                    "type": "string"
                  },
                  "ranking_result": {
                    "type": "object",
                    "properties": {
                      "certainty": {
                        "type": "string"
                      },
                      "rankings": {
                        "type": "array",
                        "items": {
                          "type": "object",
                          "properties": {
                            "principle": {
                              "type": "string"
                            },
                            "rank": {
                              "type": "integer"
                            }
                          },
                          "required": [
                            "principle",
                            "rank"
                          ],
                          "additionalProperties": false
                        }
                      }
                    },
                    "required": [
                      "certainty",
                      "rankings"
                    ],
                    "additionalProperties": false
                  }
                },
                "required": [
                  "bank_balance",
                  "memory_coming_in_this_round",
                  "ranking_result"
                ],
                "additionalProperties": false
              },
              "ranking_2": {
                "type": "object",
                "properties": {
                  "bank_balance": {
                    "type": "number"
                  },
                  "memory_coming_in_this_round": {
                    "type": "string"
                  },
                  "ranking_result": {
                    "type": "object",
                    "properties": {
                      "certainty": {
                        "type": "string"
                      },
                      "rankings": {
                        "type": "array",
                        "items": {
                          "type": "object",
                          "properties": {
                            "principle": {
                              "type": "string"
                            },
                            "rank": {
                              "type": "integer"
                            }
                          },
                          "required": [
                            "principle",
                            "rank"
                          ],
                          "additionalProperties": false
                        }
                      }
                    },
                    "required": [
                      "certainty",
                      "rankings"
                    ],
                    "additionalProperties": false
                  }
                },
                "required": [
                  "bank_balance",
                  "memory_coming_in_this_round",
                  "ranking_result"
                ],
                "additionalProperties": false
              },
              "ranking_3": {
                "type": "object",
                "properties": {
                  "bank_balance": {
                    "type": "number"
                  },
                  "memory_coming_in_this_round": {
                    "type": "string"
                  },
                  "ranking_result": {
                    "type": "object",
                    "properties": {
                      "certainty": {
                        "type": "string"
                      },
                      "rankings": {
                        "type": "array",
                        "items": {
                          "type": "object",
                          "properties": {
                            "principle": {
                              "type": "string"
                            },
                            "rank": {
                              "type": "integer"
                            }
                          },
                          "required": [
                            "principle",
                            "rank"
                          ],
                          "additionalProperties": false
                        }
                      }
                    },
                    "required": [
                      "certainty",
                      "rankings"
                    ],
                    "additionalProperties": false
                  }
                },
                "required": [
                  "bank_balance",
                  "memory_coming_in_this_round",
                  "ranking_result"
                ],
                "additionalProperties": false
              }
            },
            "required": [
              "demonstrations",
              "detailed_explanation",
              "initial_ranking",
              "ranking_2",
              "ranking_3"
            ],
            "additionalProperties": false
          },
          "phase_2": {
            "type": "object",
            "properties": {
              "post_group_discussion": {
                "type": "object",
                "properties": {
                  "bank_balance": {
                    "type": "number"
                  },
                  "class_put_in": {
                    "type": "string"
                  },
                  "final_ranking": {
                    "type": "object",
                    "properties": {
                      "certainty": {
                        "type": "string"
                      },
                      "rankings": {
                        "type": "array",
                        "items": {
                          "type": "object",
                          "properties": {
                            "principle": {
                              "type": "string"
                            },
                            "rank": {
                              "type": "integer"
                            }
                          },
                          "required": [
                            "principle",
                            "rank"
                          ],
                          "additionalProperties": false
                        }
                      }
                    },
                    "required": [
                      "certainty",
                      "rankings"
                    ],
                    "additionalProperties": false
                  },
                  "memory_coming_in_this_round": {
                    "type": "string"
                  },
                  "payoff_received": {
                    "type": "number"
                  }
                },
                "required": [
                  "bank_balance",
                  "class_put_in",
                  "final_ranking",
                  "memory_coming_in_this_round",
                  "payoff_received"
                ],
                "additionalProperties": false
              },
              "rounds": {
                "type": "array",
                "items": {
                  "type": "object",
                  "properties": {
                    "bank_balance": {
                      "type": "number"
                    },
                    "favored_principle": {
                      "type": "string"
                    },
                    "initiate_vote": {
                      "type": "string"
                    },
                    "internal_reasoning": {
                      "type": "string"
                    },
                    "memory_coming_in_this_round": {
                      "type": "string"
                    },
                    "number_discussion_round": {
                      "type": "integer"
                    },
                    "public_message": {
                      "type": "string"
                    },
                    "speaking_order": {
                      "type": "integer"
                    }
                  },
                  "required": [
                    "bank_balance",
                    "favored_principle",
                    "initiate_vote",
                    "internal_reasoning",
                    "memory_coming_in_this_round",
                    "number_discussion_round",
                    "public_message",
                    "speaking_order"
                  ],
                  "additionalProperties": false
                }
              }
            },
            "required": [
              "post_group_discussion",
              "rounds"
            ],
            "additionalProperties": false
          },
          "reasoning_enabled": {
            "type": "boolean"
          },
          "temperature": {
            "type": "number"
          }
        },
        "required": [
          "model",
          "name",
          "personality",
          "phase_1",
          "phase_2",
          "reasoning_enabled",
          "temperature"
        ],
        "additionalProperties": false
      }
    }
  },
  "required": [
    "agents",
    "general_information"
  ],
  "additionalProperties": false
}
```
