if (typeof(LNP) === 'undefined') {
  LNP = {};
}

(function(root, Drupal, $, moment) {

'use strict';

LNP.Utils = {
  getUrlParam: function(paramName) {
    var oRegex = new RegExp('[\?&]' + paramName + '=([^&]+)', 'i'),
      oMatch = oRegex.exec(document.location.search);

    if (oMatch && oMatch.length > 1) {
      return decodeURIComponent(oMatch[1]);
    } else {
      return false;
    }
  },

  // https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Global_Objects/Math/round
  round: function(number, precision) {
    precision = precision || 0;
    var factor = Math.pow(10, precision);
    var tempNumber = number * factor;
    var roundedTempNumber = Math.round(tempNumber);
    return roundedTempNumber / factor;
  }
};

LNP.matchUrl = function(gameid, league, year, subpath) {
  return Drupal.settings.basePath + 'wp/match/' + gameid + '/' + league
    + '/' + year + (subpath ? '/' + subpath : '');
};

LNP.squadraUrl = function(teamid) {
  return Drupal.settings.basePath + 'squadra/wp/' + teamid;
};

LNP.makeLink = function(url, text, attributes) {
  var attributesTemp = [];
  var k;

  attributes = attributes || {};

  for (k in attributes) {
    if (attributes.hasOwnProperty(k)) {
      if (k === 'class') {
        attributesTemp.push('class="' + Drupal.checkPlain(attributes[k].join(' ')) + '"');
      }
      else {
        attributesTemp.push(Drupal.checkPlain(k) + '="' + Drupal.checkPlain(attributes[k]) + '"');
      }
    }
  }

  attributesTemp = attributesTemp.length > 0 ? ' ' + attributesTemp.join(' ') : '';

  return '<a href="' + Drupal.checkPlain(url) + '"' + attributesTemp + '>' + text + '</a>';
};

LNP.streamLink = function(stream_url) {
  var base_url = Drupal.settings.basePath + 'sites/all/themes/custom/lnp_2023_theme/images/';
  var link_content, link_title;

  if (stream_url.match(/lnppass\./)) {
    link_content = '<img width="55" src="' + base_url + 'lnp_pass.png" alt="Logo LNP PASS" />';
    link_title = 'Guarda su LNP PASS';
  }
  else if (stream_url.match(/youtu/)) {
    link_content = '<img width="70" src="' + base_url + 'youtube.png" alt="Logo Youtube" />';
    link_title = 'Guarda su Youtube';
  }
  else if (stream_url.match(/rai2/)) {
    link_content = '<img width="38" src="' + base_url + 'Rai2.svg" alt="Logo Rai2" />';
    link_title = 'Guarda su Rai 2';
  }
  else if (stream_url.match(/rai/)) {
    link_content = '<img width="70" src="' + base_url + 'RaiSport.svg" alt="Logo RaiSport" />';
    link_title = 'Guarda su Rai Sport';
  }
  else {
    link_content = '▶ Guarda';
  }

  return LNP.makeLink(stream_url, link_content, {
    target: '_blank',
    title: link_title,
    style: 'display: inline-block',
  });
};

LNP.makeCalendario = function(rows, wp_league, wp_year) {
  var html = '';
  html += '<div class="table-wrapper">';
  html += '<table class="table table-striped">';

  html += '<thead><tr>' +
    '<th>Data</th>' +
    '<th>Casa</th>' +
    '<th>Ospite</th>' +
    '<th>Risultato</th>' +
    '<th>Tabellino</th>' +
    '<th>Impianto</th>' +
    '</tr></thead>';

  html += '<tbody>';

  $.each(rows, function() {
    var row = this;
    var tabellino = '';
    var score = '';
    var casa = '';
    var ospite = '';

    if (row.teamid_home !== '0') {
      casa = LNP.makeLink(LNP.squadraUrl(row.teamid_home), row.teamname_home);
    }

    if (row.teamid_away !== '0') {
      ospite = LNP.makeLink(LNP.squadraUrl(row.teamid_away), row.teamname_away);
    }

    if (row.game_status === 'finished') {
      tabellino = LNP.makeLink(LNP.matchUrl(row.gameid, wp_league, wp_year, 'tabellino'), 'Vedi tabellino');
      score = LNP.makeLink(LNP.matchUrl(row.gameid, wp_league, wp_year), row.score_home + ' - ' + row.score_away);
    }
    else {
      tabellino = 'ND';
      score = '0 - 0';
    }

    html += '<tr>';
    html += '<td>' + row.date + ' ' + row.time + '</td>';
    html += '<td>' + casa + '</td>';
    html += '<td>' + ospite + '</td>';
    html += '<td>' + score + '</td>';
    html += '<td>' + tabellino + '</td>';
    html += '<td>' + (row.arena ? Drupal.checkPlain(row.arena) : 'ND') + '</td>';
    html += '</tr>';
  });

  html += '</tbody>';
  html += '</table>';
  html += '</div>';

  return html;
};

LNP.makeClassifica = function(rows) {
  var html = '';
  html += '<div class="table-wrapper">';
  html += '<table class="table table-striped">';

  html += '<thead><tr>' +
    '<th>Squadra</th>' +
    '<th>PTI</th>' +
    '<th>G</th>' +
    '<th>V</th>' +
    '<th>P</th>' +
    '<th>%</th>' +
    '<th>PF</th>' +
    '<th>PS</th>' +
    '</tr></thead>';

  $.each(rows, function() {
    var row = this;

    html += '<tr>';
    html += '<td>' + LNP.makeLink(LNP.squadraUrl(row.teamid), row.teamname) +  '</td>';
    html += '<td>' + Drupal.checkPlain(row.points) + '</td>';
    html += '<td>' + Drupal.checkPlain(row.games) + '</td>';
    html += '<td>' + Drupal.checkPlain(row.win) + '</td>';
    html += '<td>' + Drupal.checkPlain(row.loss) + '</td>';
    html += '<td>' + Drupal.checkPlain(row.winpercent) + '</td>';
    html += '<td>' + Drupal.checkPlain(row.score) + '</td>';
    html += '<td>' + Drupal.checkPlain(row.against) + '</td>';
    html += '</tr>';
  });

  html += '</tbody>';
  html += '</table>';
  html += '</div>';

  return html;
};

LNP.MiddleLayerSchedule = {
  init: function($wrapper, scheduleSettings) {
    if (!$wrapper.length) {
      return;
    }

    var self = this;

    $wrapper.once('middle-layer-schedule', function() {
      var $table = self.buildTable($wrapper, scheduleSettings);
      self.populateTable($table, scheduleSettings);
    });
  },

  buildTable: function($wrapper, scheduleSettings) {
    var table = $('<table class="table table-striped"></table>');
    var tableWrapper = $('<div class="table-wrapper"></div>');

    table.prepend('<caption>Calendario ' + scheduleSettings.title + '</caption>');

    var thead = '<thead><tr>' +
      '<th>Data</th>' +
      '<th>Casa</th>' +
      '<th>Ospite</th>' +
      '<th>Risultato</th>' +
      '<th>Tabellino</th>' +
      '<th>Impianto</th>' +
      '</tr></thead>';
    var tbody = '<tbody></tbody>';

    table.append(thead + tbody);
    tableWrapper.append(table);

    $wrapper.append(tableWrapper);

    return table;
  },

  populateTable: function($table, scheduleSettings) {
    var self = this;

    if (!scheduleSettings.hasOwnProperty('round')) {
      scheduleSettings.round = 'all';
    }

    if (scheduleSettings.hasOwnProperty('schedule_phases')) {
      $.ajax({
        url: '//lnpstat.domino.it/getstatisticsfiles?task=schedule&year='
          + scheduleSettings.year + '&league=' + scheduleSettings.league
          + '&round=' + scheduleSettings.round,
        cache: false,
        success: function(scheduleData) {
          self.populateTableWithFixedPhases($table, scheduleData, scheduleSettings);
        }
      });
    }
  },

  populateTableWithFixedPhases: function($table, scheduleData, scheduleSettings) {
    var self = this;
    var matches = [];

    $.each(scheduleSettings.schedule_phases, function(phaseName, phaseDates) {
      var phaseMatches = [];
      phaseMatches.phaseName = phaseName;

      $.each(phaseDates, function(i, phaseDate) {
        $.each(scheduleData, function(matchIndex, match) {
          if (match.date == phaseDate) {
            phaseMatches.push(match);
          }
        });
      });

      matches.push(phaseMatches);
    });

    $.each(matches, function(matchPhase, matches) {
      self.addTableGroupingRow($table, matches.phaseName);

      $.each(matches, function(i, match) {
        if (match.arena == null) {
          match.arena = 'ND';
        }

        if (match.teamname_home == null) {
          match.teamname_home = 'ND';
        }
        if (match.teamname_away == null) {
          match.teamname_away = 'ND';
        }

        if (match.game_status === 'finished') {
          var matchUrl = '/wp/match/' + match.gameid + '/' + scheduleSettings.league
            + '/' + scheduleSettings.year;

          match.tabellino = '<a href="' + matchUrl + '/tabellino">Vedi tabellino</a>';
          match.score = '<a href="' + matchUrl + '">'
            + match.score_home + ' - ' + match.score_away
            +  '</a>';
        }
        else {
          match.tabellino = 'ND';
          match.score = '0 - 0';
        }

        self.addTableRow($table, {
          data: match.date + ' ' + match.time,
          casa: '<a href="/squadra/wp/' + match.teamid_home + '">' + match.teamname_home + '</a>',
          ospite: '<a href="/squadra/wp/' + match.teamid_away + '">' + match.teamname_away + '</a>',
          risultato: match.score,
          tabellino: match.tabellino,
          impianto: match.arena
        });
      });
    });
  },

  addTableRow: function($table, rowData) {
    var row = $('<tr>' +
      '<td>' + rowData.data + '</td>' +
      '<td>' + rowData.casa + '</td>' +
      '<td>' + rowData.ospite + '</td>' +
      '<td>' + rowData.risultato + '</td>' +
      '<td>' + rowData.tabellino + '</td>' +
      '<td>' + rowData.impianto + '</td>' +
      '</tr>');

    $table.find('tbody').append(row);
  },

  addTableGroupingRow: function($table, groupLabel) {
    var row = $('<tr class="grouping-row"><td colspan="6">' + groupLabel + '</td></tr>');
    $table.find('tbody').append(row);
  }
};

  Drupal.behaviors.lnpViewsTabsCount = {
    attach: function(context) {
      $('.quicktabs-tabs', context).once('tabs-count').each(function() {
        $(this).closest('.view:not(.view-fascione-squadre-multi-livello), form').addClass('tabs-count-' + $(this).children().size());
      });
    }
  };

  Drupal.behaviors.giocatoriFilter = {
    attach: function(context, settings) {
      var form = $('#lnp-giocatori-serie-form', context).once('giocatori-filter');

      if (!form.length) {
        return;
      }

      $('.tabella-filters .form-control[name="query"]', form).on('input', function() {
        var query = $(this).val();
        var splitQuery = query.split(' ');

        $('tbody tr', form).show();

        $.each(splitQuery, function(i, word) {
          $('tbody tr', form).not(':contains("' + word.toLowerCase() + '")').hide();
        });
      });
    }
  };

  Drupal.behaviors.gotoNextGirone = {
    attach: function(context, settings) {
      if ($('.bxslider-goto-next-slide').length) {
        $('.bxslider-goto-next-slide').click(function(e) {
          e.preventDefault();
          $(this).parents('.views-slideshow-bxslider').find('.bx-next').click()
        })
      }
    }
  }

  Drupal.behaviors.selectGironeMultilivello = {
    attach: function(context, settings) {
      if ($('#block-lnp-fascione-squadre-multi-lvl .quicktabs-tabs', context).length == 0) {
        return;
      }

      $('#block-lnp-fascione-squadre-multi-lvl .quicktabs-tabs a', context).click(function(e) {
        var selectedCompetition = $('#block-lnp-fascione-squadre-multi-lvl .quicktabs-tabpage:not(.quicktabs-hide) .quicktabs-tabs li.active a.active .tab-label').html();
        var selectedCompetitionID = '';
        var $round = $('#block-lnp-calendario-serie-mini [name="round"]');

        if (selectedCompetition.indexOf('Serie A2') !== -1) {
          selectedCompetitionID = 'ita2';
        }
        else if (selectedCompetition.indexOf('VERDE') !== -1) {
          selectedCompetitionID = 'ita2_a';
        }
        else if (selectedCompetition.indexOf('ROSSO') !== -1) {
          selectedCompetitionID = 'ita2_b';
        }
        else if (selectedCompetition.indexOf('BIANCO') !== -1) {
          selectedCompetitionID = 'ita2_2ph_bianco';
        }
        else if (selectedCompetition.indexOf('GIALLO') !== -1) {
          selectedCompetitionID = 'ita2_2ph_giallo';
        }
        else if (selectedCompetition.indexOf('AZZURRO') !== -1) {
          selectedCompetitionID = 'ita2_2ph_azzurro';
        }
        else if (selectedCompetition.indexOf('BLU') !== -1) {
          selectedCompetitionID = 'ita2_2ph_blu';
        }
        else if (selectedCompetition.indexOf('NERO') !== -1) {
          selectedCompetitionID = 'ita2_2ph_nero';
        }
        else if (selectedCompetition.indexOf('SALVEZZA') !== -1) {
          selectedCompetitionID = 'ita2_2ph_salvezza';
        }
        else if (selectedCompetition.indexOf('Gir.A1') !== -1) {
          selectedCompetitionID = 'ita3_a1';
        }
        else if (selectedCompetition.indexOf('Gir.A2') !== -1) {
          selectedCompetitionID = 'ita3_a2';
        }
        else if (selectedCompetition.indexOf('Gir.A') !== -1) {
          selectedCompetitionID = 'ita3_a';
        }
        else if (selectedCompetition.indexOf('Gir.B1') !== -1) {
          selectedCompetitionID = 'ita3_b1';
        }
        else if (selectedCompetition.indexOf('Gir.B2') !== -1) {
          selectedCompetitionID = 'ita3_b2';
        }
        else if (selectedCompetition.indexOf('Gir.B') !== -1) {
          selectedCompetitionID = 'ita3_b';
        }
        else if (selectedCompetition.indexOf('Gir.C1') !== -1) {
          selectedCompetitionID = 'ita3_c1';
        }
        else if (selectedCompetition.indexOf('Gir.C2') !== -1) {
          selectedCompetitionID = 'ita3_c2';
        }
        else if (selectedCompetition.indexOf('Gir.C') !== -1) {
          selectedCompetitionID = 'ita3_c';
        }
        else if (selectedCompetition.indexOf('Gir.D1') !== -1) {
          selectedCompetitionID = 'ita3_d1';
        }
        else if (selectedCompetition.indexOf('Gir.D2') !== -1) {
          selectedCompetitionID = 'ita3_d2';
        }
        else if (selectedCompetition.indexOf('Gir.D') !== -1) {
          selectedCompetitionID = 'ita3_d';
        }
        else if (selectedCompetition.indexOf('orologio') !== -1) {
          selectedCompetitionID = 'ita2_clock';
        }

        // Switch tra competizioni con numero diverso di round.
        if ($round.find('option').length !== parseInt(Drupal.settings.serie.campionati_max_round[selectedCompetitionID], 10)) {
          let options = '', i;
          for (i = 1; i <= Drupal.settings.serie.campionati_max_round[selectedCompetitionID]; i++) {
            options += '<option value="' + i + '">' + (i + '° giornata') + '</option>';
          }

          $round.html(options);
          $round.val(Drupal.settings.serie.campionati_curr_round[selectedCompetitionID]);
        }

        // La classifica della fase ad orologio (tab dedicata) deve mostrare la select per campionato.
        $('#block-lnp-classifica-serie-mini .form-item-selected-campionato').toggleClass('hidden', selectedCompetitionID !== 'ita2_clock');

        // ... e non devo impostare ita2_clock come campionato, perché i campionati sono quelli regolari!
        if (selectedCompetitionID !== 'ita2_clock') {
          $('#block-lnp-classifica-serie-mini .form-item-selected-campionato select').val(selectedCompetitionID);
        }

        $('#block-lnp-calendario-serie-mini .form-item-selected-campionato select').val(selectedCompetitionID).trigger('change');

        // Messaggio di loading comune classifica/calendario.
        $('#block-lnp-classifica-serie-mini .ajax-wrapper, #block-lnp-calendario-serie-mini .ajax-wrapper').html(Drupal.t('Caricamento in corso...'));
      });

      $('#block-lnp-fascione-squadre-multi-lvl .quicktabs-tabs a:first', context).click();
    }
  }

  Drupal.behaviors.tableSorter = {
    attach: function(context, settings) {
      if ($('table.with-tablesorter').length) {
        $('table.with-tablesorter').once('tablesorter').tablesorter();
      }
    }
  };

  Drupal.behaviors.lnp = {
    attach: function(context, settings) {
      $('[data-player-id]').once('lnp-player-link', function() {
        $(this).on('click', function() {
          var id = $(this).data('player-id');
          window.location.href = '/giocatore/wp/' + id;
        });
      });
    }
  };

  Drupal.behaviors.infograficaTiriGiocatore = {
    attach: function(context, settings) {
      if (!$('#lnp-form-infografica-tiri-giocatore').length) {
        return;
      }

      $('#lnp-form-infografica-tiri-giocatore').once('infografica-tiri-giocatore', function() {

        $(this).find('select[name="campionato"]').on('change', function() {
          updateInfografica();
        });

        updateInfografica();
      });

      function updateInfografica() {
        var $infografica = $('#lnp-form-infografica-tiri-giocatore');
        var selectedCampionato = $infografica.find('select[name="campionato"]').val();
        var statsCampionato = Drupal.settings.lnp_stats_giocatore[selectedCampionato];

        var round = LNP.Utils.round;

        // Assicura che ci siano dati, anche se nulli.
        statsCampionato = statsCampionato || {
          total: {},
          avg: {}
        };

        $.each(['p2m', 'p2a', 'p3m', 'p3a', 'ftm', 'fta'], function(i, key) {
          if (!statsCampionato['total'][key]) {
            statsCampionato['total'][key] = 0;
          }

          if (!statsCampionato['avg'][key]) {
            statsCampionato['avg'][key] = 0;
          }
        });

        // Assembla le statistiche disponibili.
        var stats = {
          // Totali
          'total:p2m': statsCampionato['total']['p2m'],
          'total:p2a': statsCampionato['total']['p2a'],
          'total:p3m': statsCampionato['total']['p3m'],
          'total:p3a': statsCampionato['total']['p3a'],
          'total:ftm': statsCampionato['total']['ftm'],
          'total:fta': statsCampionato['total']['fta'],

          // Medie.
          'avg:p2m': round(statsCampionato['avg']['p2m'], 2),
          'avg:p2a': round(statsCampionato['avg']['p2a'], 2),
          'avg:p3m': round(statsCampionato['avg']['p3m'], 2),
          'avg:p3a': round(statsCampionato['avg']['p3a'], 2),
          'avg:ftm': round(statsCampionato['avg']['ftm'], 2),
          'avg:fta': round(statsCampionato['avg']['fta'], 2),

          // Percentuali.
          // 'avg:p2p': statsCampionato['avg']['p2a'] ? round(round(statsCampionato['avg']['p2m'], 2) / round(statsCampionato['avg']['p2a'], 2) * 100) : 0,
          'avg:p2p': statsCampionato['avg']['p2a'] ? round(statsCampionato['total']['p2m'] / statsCampionato['total']['p2a'] * 100) : 0,
          // 'avg:p3p': statsCampionato['avg']['p3a'] ? round(round(statsCampionato['avg']['p3m'], 2) / round(statsCampionato['avg']['p3a'], 2) * 100) : 0,
          'avg:p3p': statsCampionato['avg']['p3a'] ? round(statsCampionato['total']['p3m'] / statsCampionato['total']['p3a'] * 100) : 0,
          // 'avg:ftp': statsCampionato['avg']['fta'] ? round(round(statsCampionato['avg']['ftm'], 2) / round(statsCampionato['avg']['fta'], 2) * 100) : 0
          'avg:ftp': statsCampionato['avg']['fta'] ? round(statsCampionato['total']['ftm'] / statsCampionato['total']['fta'] * 100) : 0,
        };

        var statFunctions = {
          'circle_dasharray': function(el, value) {
            $(el).attr('stroke-dasharray', value.replace(',', '.') + ',100');
          }
        };

        // Formatta i decimali usando la notazione italiana (virgola anziché il punto).
        $.each(stats, function(key) {
          stats[key] = String(stats[key]).replace('.', ',');
        });

        // Popola gli elementi html con le statistiche.
        $('[data-stat]', $infografica).each(function() {
          var statKey = $(this).attr('data-stat');
          var statFunction = $(this).attr('data-function');

          if (statFunction && statFunctions[statFunction]) {
            statFunctions[statFunction](this, stats[statKey] || '');
          }
          else {
            $(this).text(stats[statKey] || '');
          }
        });
      }
    }
  };

  /**
   * I BEAN di tipo "Banner" vengono trasformati in owlCarousel se questi
   * hanno più di un field-item.
   */
  Drupal.behaviors.bannerCarousel = {
    attach: function(context, settings) {
      $('.block-bean-banner').each(function(i, banner) {
        if (!$(banner).find('.field-name-field-immagine-con-link > .field-items > .field-item.odd').length) {
          return;
        }

        $(banner).once('banner-carousel').find('.field-name-field-immagine-con-link > .field-items')
          .addClass('owl-carousel').owlCarousel({
          items: 1,
          loop: true,
          dots: false,
          autoplay: true,
          autoplayTimeout: 3000,
          autoplayHoverPause: true
        });
      });
    }
  };

}(window, Drupal, jQuery, moment));
;
