// The deck client (GN25): no framework, no build step, stdlib browser only.
// It reads the mounts the shell renders on <main id="feed"> — data-world,
// data-worlds, data-generator — and builds the snap-scroll deck inside the
// main: the top bar (world switch, generator dot), the scroller (one card
// per viewport, the verb rail, the prompt bar) and the edit sheet. The
// no-JS article list below the mounts stays in the DOM, hidden by the
// stylesheet once this script adds its class — the shell is one page for
// both paths.
//
// Every fetch is same-origin (relative paths only); there is no eval and no
// inline handler anywhere — listeners are attached by name below.

;(function () {
  'use strict'

  var main = document.getElementById('feed')
  if (!main) {
    return
  }

  var world = main.getAttribute('data-world') || ''
  var allWorlds = (main.getAttribute('data-worlds') || '')
    .split(',')
    .map(function (name) {
      return name.trim()
    })
    .filter(function (name) {
      return name
    })

  var cards = [] // { name, img, prompt, seed, liked, el, imgEl }
  var cursor = null
  var current = -1 // the settled card's index
  var loading = false
  var genOn = false // the world's generation state (GN44)
  var seenNames = {} // per world: names already reported consumed
  var warmed = {} // per world: img paths already handed to new Image()
  var pollTimer = null
  var PLACEHOLDER_WINDOW = 2 // cards either side of the settled one kept in the DOM

  main.classList.add('js')

  // ---- the scaffold ------------------------------------------------------

  var topbar = document.createElement('div')
  topbar.className = 'topbar'

  var titleEl = document.createElement('span')
  titleEl.className = 'title'
  titleEl.textContent = world
  topbar.appendChild(titleEl)

  var switchEl = document.createElement('div')
  switchEl.className = 'switch'
  allWorlds.forEach(function (name) {
    var button = document.createElement('button')
    button.type = 'button'
    button.textContent = name
    button.className = name === world ? 'world on' : 'world'
    button.addEventListener('click', function () {
      switchWorld(name)
    })
    switchEl.appendChild(button)
  })
  topbar.appendChild(switchEl)

  var dot = document.createElement('span')
  dot.className = 'dot'
  dot.textContent = 'generator ' + (main.getAttribute('data-generator') || '')
  topbar.appendChild(dot)

  // GN44 — the generation status and its toggle: deck chrome beside the
  // dot, always visible, never inside a collapsed menu (Interfaces 6).
  // On and off differ by word, not hue (Interfaces 7): the element's
  // literal text is `generating` or `paused`, a change is announced
  // rather than silently repainted, and the toggle's pressed state
  // mirrors it. The toggle is a labelled pill like the world switch
  // (GN28's rule: no word is asked to fit inside a glyph circle).
  // GN45 — the supervisor's phase rides the same element as a second
  // word beside the state, inside the same aria-live region so one
  // announcement covers both. Each phase is a word (never a colour
  // alone); the map lookup means a value outside it paints nothing,
  // never raw text.
  var GEN_ON = '<b>generating</b>'
  var GEN_OFF = '<b>paused</b>'
  var PHASE_WORDS = {
    authoring: '<i>authoring</i>',
    mutating: '<i>mutating</i>',
    rendering: '<i>rendering</i>',
    waiting: '<i>waiting</i>',
    halted: '<i>halted</i>',
    stale: '<i>stale</i>',
  }

  var genstate = document.createElement('span')
  genstate.className = 'genstate'
  genstate.setAttribute('aria-live', 'polite')
  topbar.appendChild(genstate)

  var genToggle = document.createElement('button')
  genToggle.type = 'button'
  genToggle.className = 'gentoggle'
  genToggle.textContent = 'generation'
  genToggle.addEventListener('click', function () {
    postGeneration(!genOn)
  })
  topbar.appendChild(genToggle)

  main.appendChild(topbar)

  var scroller = document.createElement('div')
  scroller.className = 'scroller'
  main.appendChild(scroller)

  var sheet = document.createElement('div')
  sheet.className = 'sheet'
  sheet.hidden = true

  var sheetField = document.createElement('p')
  sheetField.className = 'sheet-field'
  var textarea = document.createElement('textarea')
  textarea.setAttribute('aria-label', 'prompt')
  sheetField.appendChild(textarea)

  var sheetRow = document.createElement('p')
  sheetRow.className = 'sheet-row'
  var editButton = document.createElement('button')
  editButton.type = 'button'
  editButton.textContent = 'regenerate'
  var cancelButton = document.createElement('button')
  cancelButton.type = 'button'
  cancelButton.className = 'cancel'
  cancelButton.textContent = 'cancel'
  sheetRow.appendChild(editButton)
  sheetRow.appendChild(cancelButton)

  sheet.appendChild(sheetField)
  sheet.appendChild(sheetRow)
  main.appendChild(sheet)

  // ---- helpers -----------------------------------------------------------

  function setDot(state) {
    dot.textContent = 'generator ' + state
    dot.setAttribute('data-state', state)
  }

  function setGenState(on, phase) {
    genOn = on
    var markup = on ? GEN_ON : GEN_OFF
    // GN45: the phase word paints only beside `generating` — the feed
    // carries no phase when the supervisor is not live, and the map
    // lookup refuses anything it does not know.
    if (on && PHASE_WORDS[phase]) {
      markup += ' ' + PHASE_WORDS[phase]
      genstate.setAttribute('data-phase', phase)
    } else {
      genstate.removeAttribute('data-phase')
    }
    genstate.innerHTML = markup
    genstate.setAttribute('data-state', on ? 'on' : 'off')
    genToggle.setAttribute('aria-pressed', on ? 'true' : 'false')
    genToggle.className = on ? 'gentoggle on' : 'gentoggle'
  }

  function postGeneration(on) {
    fetch('/w/' + world + '/generation', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Accept: 'application/json',
      },
      body: JSON.stringify({ on: on }),
    })
      .then(function (resp) {
        return resp.json()
      })
      .then(function (doc) {
        if (doc.ok) {
          setGenState(doc.generation === 'on', doc.phase)
        }
      })
      .catch(function () {})
  }

  function postForm(path, pairs) {
    var body = new URLSearchParams()
    pairs.forEach(function (pair) {
      body.append(pair[0], pair[1])
    })
    return fetch(path, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/x-www-form-urlencoded',
        Accept: 'application/json',
      },
      body: body.toString(),
    }).then(function (resp) {
      return resp.json()
    })
  }

  function currentCard() {
    return cards[current]
  }

  // ---- the cards ---------------------------------------------------------

  // GN28 — the verb rail's markup. Each control is a glyph-only circle
  // with its word in a sibling label outside it: measured on the landed
  // build, `regenerate` laid out at 59px inside the button's 42px content
  // box, so no word is ever asked to fit a 44px circle again. The
  // accessible name is the button's aria-label, never the glyph. The gap
  // before dislike is its own element — the mis-tap mitigation for the
  // hard delete, not a margin on a neighbour.
  var RAIL_HTML =
    '<div class="slot"><button type="button" class="like" aria-label="Like">♥</button>' +
    '<span class="lab">like</span></div>' +
    '<div class="slot"><button type="button" class="regen" aria-label="Regenerate">↻</button>' +
    '<span class="lab">regenerate</span></div>' +
    '<div class="gap"></div>' +
    '<div class="slot"><button type="button" class="dislike" aria-label="Dislike">✕</button>' +
    '<span class="lab">dislike</span></div>'

  function makeCard(card, at) {
    var el = document.createElement('section')
    el.className = 'card'

    var img = document.createElement('img')
    img.alt = card.name
    img.src = card.img
    el.appendChild(img)

    var rail = document.createElement('div')
    rail.className = 'rail'
    rail.innerHTML = RAIL_HTML
    rail.querySelector('button.like').addEventListener('click', function () {
      likeCard(card)
    })
    rail.querySelector('button.regen').addEventListener('click', function () {
      regenerateCard(card)
    })
    rail.querySelector('button.dislike').addEventListener('click', function () {
      dislikeCard(card)
    })
    el.appendChild(rail)

    var bar = document.createElement('div')
    bar.className = 'promptbar'
    bar.textContent = card.prompt || ''
    bar.addEventListener('click', function () {
      openSheet(card)
    })
    el.appendChild(bar)

    var holder = {
      name: card.name,
      img: card.img,
      prompt: card.prompt,
      seed: card.seed,
      liked: card.liked,
      el: el,
      imgEl: img,
    }
    if (typeof at === 'number') {
      scroller.insertBefore(el, scroller.children[at] || null)
      cards.splice(at, 0, holder)
    } else {
      scroller.appendChild(el)
      cards.push(holder)
    }
    return holder
  }

  // The window of ~5: a card far from the settled one keeps its place and
  // its height (every card is a full viewport tall) but drops its image —
  // a spacer — and takes it back (recycled) when the scroll returns.
  function windowNear(idx) {
    cards.forEach(function (card, i) {
      var near = Math.abs(i - idx) <= PLACEHOLDER_WINDOW
      var has = card.el.contains(card.imgEl)
      if (near && !has) {
        card.el.insertBefore(card.imgEl, card.el.firstChild)
      } else if (!near && has) {
        card.el.removeChild(card.imgEl)
      }
    })
  }

  // Warm the next two images so a swipe lands on a painted picture, not a
  // decode — the warm-up reports nothing consumed.
  function warmAhead() {
    ;[current + 1, current + 2].forEach(function (i) {
      var card = cards[i]
      if (!card || warmed[card.img]) {
        return
      }
      warmed[card.img] = true
      var probe = new Image()
      probe.src = card.img
    })
  }

  // ---- the settle --------------------------------------------------------

  var settleTimer = null
  scroller.addEventListener('scroll', function () {
    if (settleTimer) {
      clearTimeout(settleTimer)
    }
    settleTimer = setTimeout(settle, 250)
  })

  function settle() {
    var height = scroller.clientHeight
    if (!height) {
      return
    }
    var idx = Math.round(scroller.scrollTop / height)
    if (idx < 0 || idx >= cards.length || idx === current) {
      return
    }
    current = idx
    afterSettle()
  }

  function afterSettle() {
    windowNear(current)
    warmAhead()
    // Exactly the settled card is reported consumed — never a prefetched
    // one (the unseen count is the generation demand signal).
    var card = currentCard()
    if (card && !seenNames[card.name]) {
      seenNames[card.name] = true
      postForm('/w/' + world + '/seen', [['names', card.name]]).catch(function () {})
    }
    // Near the end of the loaded deck, pull the next page behind the
    // same cursor.
    if (cursor && current >= cards.length - 3 && !loading) {
      fetchDeck(false)
    }
  }

  function scrollToIndex(idx) {
    if (idx < 0 || idx >= cards.length) {
      return
    }
    scroller.scrollTop = idx * scroller.clientHeight
  }

  // ---- the deck fetch ----------------------------------------------------

  function fetchDeck(reset) {
    if (loading) {
      return
    }
    loading = true
    var path = '/w/' + world + '/deck?n=10'
    if (cursor && !reset) {
      path += '&cursor=' + encodeURIComponent(cursor)
    }
    fetch(path)
      .then(function (resp) {
        return resp.json()
      })
      .then(function (doc) {
        loading = false
        if (doc.generator) {
          setDot(doc.generator)
        }
        if (doc.generation) {
          setGenState(doc.generation === 'on', doc.phase)
        }
        if (reset) {
          scroller.textContent = ''
          cards = []
          current = -1
        }
        cursor = doc.cursor
        doc.cards.forEach(function (card) {
          makeCard(card)
        })
        if (current === -1 && cards.length) {
          current = 0
          afterSettle()
        } else {
          windowNear(current)
        }
      })
      .catch(function () {
        loading = false
      })
  }

  // ---- the verbs ---------------------------------------------------------

  function likeCard(card) {
    postForm('/w/' + world + '/like', [['name', card.name]]).then(function (doc) {
      if (doc.ok) {
        card.liked = true
        card.el.classList.add('liked')
      }
    })
  }

  function dislikeCard(card) {
    postForm('/w/' + world + '/dislike', [['name', card.name]]).then(function (doc) {
      if (!doc.ok) {
        return
      }
      var idx = cards.indexOf(card)
      if (idx < 0) {
        return
      }
      cards.splice(idx, 1)
      card.el.parentNode.removeChild(card.el)
      if (current >= idx) {
        current = Math.max(0, current - 1)
      }
      if (current >= cards.length) {
        current = cards.length - 1
      }
      if (cards.length) {
        scrollToIndex(current)
      }
    })
  }

  function regenerateCard(card) {
    postForm('/w/' + world + '/regenerate', [['name', card.name]])
  }

  // ---- the edit sheet ----------------------------------------------------

  var sheetCard = null

  function openSheet(card) {
    sheetCard = card
    textarea.value = card.prompt || ''
    sheet.hidden = false
    textarea.focus()
  }

  function closeSheet() {
    sheet.hidden = true
    sheetCard = null
  }

  cancelButton.addEventListener('click', closeSheet)

  function addPlaceholder(afterIdx, prompt) {
    var el = document.createElement('section')
    el.className = 'card placeholder'
    var note = document.createElement('p')
    note.className = 'note'
    note.textContent = 'rendering…'
    el.appendChild(note)
    var shown = document.createElement('p')
    shown.className = 'note'
    shown.textContent = prompt
    el.appendChild(shown)
    var at = afterIdx + 1
    var holder = { name: '', img: '', prompt: prompt, seed: null, liked: false, el: el, imgEl: el }
    scroller.insertBefore(el, scroller.children[at] || null)
    cards.splice(at, 0, holder)
    return holder
  }

  function markPlaceholder(holder, text) {
    var note = holder.el.querySelector('.note')
    if (note) {
      note.textContent = text
    }
  }

  function pollJob(jobId, holder) {
    if (pollTimer) {
      clearTimeout(pollTimer)
    }
    pollTimer = setTimeout(function () {
      fetch('/w/' + world + '/jobs')
        .then(function (resp) {
          return resp.text()
        })
        .then(function (text) {
          var lines = text.split('\n')
          for (var i = 0; i < lines.length; i++) {
            if (lines[i].indexOf(jobId) !== 0) {
              continue
            }
            var parts = lines[i].split(/\s+/)
            if (parts[1] === 'done') {
              markPlaceholder(holder, 'done')
              fetchDeck(true)
              return
            }
            if (parts[1] === 'failed') {
              markPlaceholder(holder, 'failed')
              return
            }
          }
          pollJob(jobId, holder)
        })
        .catch(function () {
          pollJob(jobId, holder)
        })
    }, 5000)
  }

  editButton.addEventListener('click', function () {
    if (!sheetCard) {
      return
    }
    var prompt = textarea.value.trim()
    if (!prompt) {
      return
    }
    var name = sheetCard.name
    var idx = cards.indexOf(sheetCard)
    closeSheet()
    postForm('/w/' + world + '/edit', [
      ['name', name],
      ['prompt', prompt],
    ]).then(function (doc) {
      if (!doc.ok || idx < 0) {
        return
      }
      var holder = addPlaceholder(idx, prompt)
      pollJob(doc.job, holder)
    })
  })

  // ---- the world switch --------------------------------------------------

  function switchWorld(target) {
    if (target === world || !target) {
      return
    }
    world = target
    seenNames = {}
    warmed = {}
    if (pollTimer) {
      clearTimeout(pollTimer)
      pollTimer = null
    }
    titleEl.textContent = world
    Array.prototype.forEach.call(switchEl.children, function (button) {
      button.className = button.textContent === world ? 'world on' : 'world'
    })
    // The deck swaps at once — browsing needs no GPU — while the handover
    // is asked for separately. The dot holds its optimistic label until
    // the next deck fetch carries the real state (the accepted gap).
    setDot('starting ' + world)
    cursor = null
    fetchDeck(true)
    postForm('/w/' + world + '/activate', []).then(
      function (doc) {
        if (doc.ok) {
          return
        }
        if (doc.error === 'flip guard') {
          // A wait state, no retry loop — an impatient thumb cannot
          // thrash the GPU and the client does not help it.
          setDot('wait ' + (doc.retry_after || 0) + 's')
        } else {
          setDot('handover failed')
        }
      },
      function () {
        setDot('handover failed')
      },
    )
  }

  // ---- the keyboard ------------------------------------------------------

  document.addEventListener('keydown', function (event) {
    if (!sheet.hidden) {
      if (event.key === 'Escape') {
        closeSheet()
      }
      return
    }
    var card = currentCard()
    if (!card) {
      return
    }
    if (event.key === 'j') {
      scrollToIndex(current + 1)
    } else if (event.key === 'k') {
      scrollToIndex(current - 1)
    } else if (event.key === 'l') {
      likeCard(card)
    } else if (event.key === 'd') {
      dislikeCard(card)
    } else if (event.key === 'r') {
      regenerateCard(card)
    } else if (event.key === 'e') {
      openSheet(card)
    }
  })

  // ---- the start ---------------------------------------------------------

  // The status word paints from the shell's mount before the first deck
  // fetch confirms it (Interfaces 6: obvious at a glance, from load on).
  // GN45: the phase word rides the same mount (data-phase), so both
  // words are on the chrome from load on.
  setGenState(main.getAttribute('data-generation') === 'on', main.getAttribute('data-phase'))
  fetchDeck(true)
})()
