/**
 * Import/Export async task handler.
 * Intercepts forms with [data-import-task] or [data-export-task] and shows a
 * loading overlay with progress bar, minimize button, and session persistence.
 *
 * This script is for import/export flows (attendees, speakers, schedule, orders).
 * General async tasks are handled by pretixbase/js/asynctask.js via [data-asynctask].
 */

let currentTaskType = null // 'import' or 'export'
let taskId = null
let checkUrl = null
let pollTimeout = null
let isLong = false
let isSubmitting = false
let isDownload = false

const getStorageKey = (type) => `eventyay_async_task_${type}`

const modal = (type) => {
    let el = document.getElementById(`${type}-loadingmodal`)
    if (!el) {
        const original = document.getElementById('loadingmodal')
        if (original) {
            el = original.cloneNode(true)
            el.id = `${type}-loadingmodal`
            document.body.appendChild(el)
        }
    }
    return el
}

const show = (headline, type) => {
    const el = modal(type)
    if (!el) return
    const h3 = el.querySelector('h3')
    if (h3) h3.textContent = headline
    const progress = el.querySelector('.progress')
    if (progress) progress.style.display = ''
    const bar = el.querySelector('.progress-bar')
    if (bar) {
        bar.style.width = '0%'
        bar.classList.add('progress-bar-striped', 'active')
    }
    const minimizeBtn = el.querySelector('.loadingmodal-minimize')
    if (minimizeBtn) minimizeBtn.style.display = ''
    document.body.classList.remove(`${type}-loading-minimized`)
    document.body.classList.add(`${type}-loading`)
    document.body.classList.add(`is-${type}-task`)
}

const hide = (type) => {
    if (pollTimeout) {
        clearTimeout(pollTimeout)
        pollTimeout = null
    }
    taskId = null
    checkUrl = null
    isSubmitting = false
    document.body.classList.remove(`${type}-loading`)
    document.body.classList.remove(`${type}-loading-minimized`)
    document.body.classList.remove(`is-${type}-task`)
    sessionStorage.removeItem(getStorageKey(type))
    currentTaskType = null
}

const setStatus = (text, type) => {
    const el = modal(type)
    if (!el) return
    const p = el.querySelector('p.status')
    if (p) p.textContent = text
}

const setProgress = (pct, type) => {
    const el = modal(type)
    if (!el) return
    const progress = el.querySelector('.progress')
    const bar = el.querySelector('.progress-bar')
    if (progress) progress.style.display = ''
    if (bar) {
        bar.style.width = pct + '%'
    }
}

const poll = () => {
    const type = currentTaskType
    fetch(checkUrl, { headers: { 'X-Requested-With': 'XMLHttpRequest' } })
        .then(r => {
            if (!r.ok) {
                throw new Error('Network response was not ok')
            }
            return r.json()
        })
        .then(data => {
            if (data.ready) {
                const bar = document.querySelector(`#${type}-loadingmodal .progress-bar`)
                const btnIcon = document.querySelector(`#${type}-loadingmodal .loadingmodal-minimize i`)
                const h3 = document.querySelector(`#${type}-loadingmodal h3`)
                const bigIcon = document.querySelector(`#${type}-loadingmodal .big-rotating-icon`)

                if (bar) {
                    bar.classList.remove('progress-bar-striped', 'active')
                    bar.style.width = '100%'
                }
                
                if (data.success || typeof data.success === 'undefined') {
                    if (bar) bar.classList.add('bg-success', 'progress-bar-success')
                    if (btnIcon) btnIcon.className = 'fa fa-check'
                    if (h3) h3.textContent = gettext('Task completed')
                    if (bigIcon) {
                        bigIcon.className = 'fa fa-check big-rotating-icon'
                        bigIcon.style.animation = 'none'
                        bigIcon.style.color = '#5cb85c'
                    }
                } else {
                    if (bar) bar.classList.add('bg-danger', 'progress-bar-danger')
                    if (btnIcon) btnIcon.className = 'fa fa-times'
                    if (h3) h3.textContent = data.message || gettext('Task failed')
                    if (bigIcon) {
                        bigIcon.className = 'fa fa-times big-rotating-icon'
                        bigIcon.style.animation = 'none'
                        bigIcon.style.color = '#d9534f'
                    }
                }

                sessionStorage.removeItem(getStorageKey(type))

                setTimeout(() => {
                    hide(type)
                    if (data.redirect && (data.success || typeof data.success === 'undefined')) {
                        location.href = data.redirect
                    }
                }, 2000)
                return
            }
            if (typeof data.percentage === 'number') {
                setProgress(data.percentage, type)
            }
            if (isLong) {
                if (data.started) {
                    setStatus(gettext('Your request is currently being processed. Depending on the size of your event, this might take up to a few minutes.'), type)
                } else {
                    setStatus(gettext('Your request has been queued on the server and will soon be processed.'), type)
                }
            }
            pollTimeout = setTimeout(poll, 250)
        })
        .catch((err) => {
            setStatus(gettext('We currently cannot reach the server, but we keep trying. ') + err.message, type)
            pollTimeout = setTimeout(poll, 5000)
        })
}

const submit = (form, type) => {
    if (isSubmitting) return
    isSubmitting = true
    currentTaskType = type

    const headline = form.getAttribute(`data-${type}-task-headline`) || gettext('We are processing your request …')
    isLong = form.hasAttribute(`data-${type}-task-long`)
    isDownload = form.hasAttribute(`data-${type}-task-download`)
    
    show(headline, type)
    setStatus(gettext('We are currently sending your request to the server.'), type)

    const body = new URLSearchParams(new FormData(form))
    body.append('ajax', '1')

    fetch(form.action || location.href, {
        method: 'POST',
        body,
        headers: { 'X-Requested-With': 'XMLHttpRequest' },
    })
        .then(async r => {
            const contentType = r.headers.get('content-type')
            if (contentType && contentType.includes('text/html')) {
                const html = await r.text()
                const newDoc = new DOMParser().parseFromString(html, 'text/html')
                const newWrapper = newDoc.querySelector('#page-wrapper')
                const oldWrapper = document.querySelector('#page-wrapper')
                if (newWrapper && oldWrapper) {
                    oldWrapper.replaceWith(newWrapper)
                } else {
                    document.documentElement.replaceWith(newDoc.documentElement)
                }
                hide(type)
                return null
            }
            if (!r.ok) {
                throw new Error('Network response was not ok')
            }
            return r.json()
        })
        .then(data => {
            if (!data) return
            if (data.redirect) {
                hide(type)
                location.href = data.redirect
                return
            }
            if (!data.check_url) {
                throw new Error('check_url missing')
            }
            taskId = data.async_id
            checkUrl = data.check_url

            sessionStorage.setItem(getStorageKey(type), JSON.stringify({
                id: taskId,
                checkUrl: checkUrl,
                isLong: isLong,
                isDownload: isDownload,
                headline: document.querySelector(`#${type}-loadingmodal h3`) ? document.querySelector(`#${type}-loadingmodal h3`).textContent : '',
                minimized: document.body.classList.contains(`${type}-loading-minimized`),
                path: location.pathname
            }))

            if (isLong && data.started) {
                setStatus(gettext('Your request is currently being processed. Depending on the size of your event, this might take up to a few minutes.'), type)
            }
            pollTimeout = setTimeout(poll, 100)
        })
        .catch(() => {
            hide(type)
            alert(gettext('An error occurred. Please try again.'))
        })
}

const restoreTask = (type) => {
    const storedTask = sessionStorage.getItem(getStorageKey(type))
    if (!storedTask) return false

    try {
        const task = JSON.parse(storedTask)
        taskId = task.id
        checkUrl = task.checkUrl
        isLong = task.isLong
        isDownload = task.isDownload
        currentTaskType = type

        show(task.headline || gettext('We are processing your request …'), type)
        
        // Auto-minimize if we navigated to a different page while task is running
        if (task.minimized || task.path !== location.pathname) {
            document.body.classList.add(`${type}-loading-minimized`)
            if (!task.minimized) {
                task.minimized = true
                task.path = location.pathname
                sessionStorage.setItem(getStorageKey(type), JSON.stringify(task))
            }
        }

        pollTimeout = setTimeout(poll, 100)
        return true
    } catch (e) {
        sessionStorage.removeItem(getStorageKey(type))
        return false
    }
}

const init = () => {
    ['import', 'export'].forEach(type => {
        const forms = document.querySelectorAll(`form[data-${type}-task]`)
        const storedTask = sessionStorage.getItem(getStorageKey(type))
        if (forms.length > 0 || storedTask) {
            const content = document.querySelector('#loadingmodal .modal-card-content')
            if (content && !content.querySelector('.loadingmodal-minimize')) {
                const div = document.createElement('div')
                div.className = 'pull-right'
                const btn = document.createElement('button')
                btn.type = 'button'
                btn.className = 'btn btn-default btn-xs loadingmodal-minimize'
                btn.title = gettext('Minimize')
                const icon = document.createElement('i')
                icon.className = 'fa fa-window-minimize'
                btn.appendChild(icon)
                div.appendChild(btn)
                content.insertBefore(div, content.firstChild)
            }
        }
    })

    document.addEventListener('submit', (e) => {
        const importForm = e.target.closest('form[data-import-task]')
        const exportForm = e.target.closest('form[data-export-task]')
        
        if (importForm) {
            e.preventDefault()
            submit(importForm, 'import')
        } else if (exportForm) {
            e.preventDefault()
            submit(exportForm, 'export')
        }
    })

    document.addEventListener('click', (e) => {
        const btn = e.target.closest('.loadingmodal-minimize')
        if (!btn) return
        e.preventDefault()
        
        const type = document.body.classList.contains('is-import-task') ? 'import' : 
                     (document.body.classList.contains('is-export-task') ? 'export' : null)
        if (!type) return

        document.body.classList.toggle(`${type}-loading-minimized`)

        const storedTask = sessionStorage.getItem(getStorageKey(type))
        if (storedTask) {
            try {
                const task = JSON.parse(storedTask)
                task.minimized = document.body.classList.contains(`${type}-loading-minimized`)
                sessionStorage.setItem(getStorageKey(type), JSON.stringify(task))
            } catch (err) {}
        }
    })

    if (!restoreTask('import')) {
        restoreTask('export')
    }
}

if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init)
} else {
    init()
}
