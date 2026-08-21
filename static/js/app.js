document.addEventListener('click', function(e){
  const target=e.target.closest('[data-confirm]');
  if(target && !confirm(target.dataset.confirm)){e.preventDefault();}
});

/* ============================================================
   OPENPIT_DASHBOARD_3D_V5
   ============================================================ */

(function () {

    const stage =
        document.getElementById('pitStage');

    const surface =
        document.querySelector('.ms-pit-surface');

    if (!stage || !surface) {
        return;
    }

    let rotateX = 55;
    let rotateZ = -1;
    let zoom = 1.04;

    let dragging = false;

    let startX = 0;
    let startY = 0;

    let initialX = rotateX;
    let initialZ = rotateZ;

    function render() {

        surface.style.setProperty(
            '--pit-rotate-x',
            rotateX + 'deg'
        );

        surface.style.setProperty(
            '--pit-rotate-z',
            rotateZ + 'deg'
        );

        surface.style.setProperty(
            '--pit-scale',
            zoom
        );
    }

    function reset() {

        rotateX = 55;
        rotateZ = -1;
        zoom = 1.04;

        surface.classList.remove(
            'is-dragging'
        );

        render();
    }

    stage.addEventListener(
        'pointerdown',
        function (event) {

            if (
                event.target.closest(
                    '.ms-zone-marker, button, a'
                )
            ) {
                return;
            }

            dragging = true;

            startX = event.clientX;
            startY = event.clientY;

            initialX = rotateX;
            initialZ = rotateZ;

            surface.classList.add(
                'is-dragging'
            );

            if (stage.setPointerCapture) {
                stage.setPointerCapture(
                    event.pointerId
                );
            }
        }
    );

    stage.addEventListener(
        'pointermove',
        function (event) {

            if (!dragging) {
                return;
            }

            const dx =
                event.clientX - startX;

            const dy =
                event.clientY - startY;

            rotateZ = Math.max(
                -28,
                Math.min(
                    28,
                    initialZ + dx * .16
                )
            );

            rotateX = Math.max(
                38,
                Math.min(
                    72,
                    initialX - dy * .14
                )
            );

            render();
        }
    );

    function stop(event) {

        if (!dragging) {
            return;
        }

        dragging = false;

        surface.classList.remove(
            'is-dragging'
        );

        if (
            stage.releasePointerCapture &&
            stage.hasPointerCapture &&
            stage.hasPointerCapture(
                event.pointerId
            )
        ) {

            stage.releasePointerCapture(
                event.pointerId
            );

        }
    }

    stage.addEventListener(
        'pointerup',
        stop
    );

    stage.addEventListener(
        'pointercancel',
        stop
    );

    stage.addEventListener(
        'wheel',
        function (event) {

            event.preventDefault();

            zoom +=
                event.deltaY < 0
                    ? .08
                    : -.08;

            zoom = Math.max(
                .88,
                Math.min(
                    1.85,
                    zoom
                )
            );

            render();

        },
        { passive: false }
    );

    const resetButton =
        document.getElementById(
            'resetButton'
        );

    if (resetButton) {

        resetButton.addEventListener(
            'click',
            reset
        );

    }

    const panel =
        document.getElementById(
            'zoneInfoPanel'
        );

    const close =
        document.getElementById(
            'zoneInfoClose'
        );

    const markers =
        document.querySelectorAll(
            '.ms-zone-marker'
        );

    function showZone(marker) {

        if (!panel) {
            return;
        }

        markers.forEach(
            function (item) {

                item.classList.remove(
                    'zone-focused'
                );

            }
        );

        marker.classList.add(
            'zone-focused'
        );

        const values = {

            zoneInfoLetter:
                marker.dataset.letter || '',

            zoneInfoName:
                marker.dataset.zone || '',

            zoneInfoDescription:
                marker.dataset.description ||
                'No recent sensor reading is available.',

            zoneInfoRisk:
                marker.dataset.risk === '--'
                    ? '--'
                    : marker.dataset.risk + '%',

            zoneInfoFs:
                marker.dataset.fs || '--',

            zoneInfoDisplacement:
                marker.dataset.displacement === '--'
                    ? '--'
                    : marker.dataset.displacement + ' mm',

            zoneInfoRainfall:
                marker.dataset.rainfall === '--'
                    ? '--'
                    : marker.dataset.rainfall + ' mm'
        };

        Object.entries(values).forEach(
            function ([id, value]) {

                const element =
                    document.getElementById(id);

                if (element) {
                    element.textContent = value;
                }

            }
        );

        panel.hidden = false;
    }

    markers.forEach(
        function (marker) {

            marker.addEventListener(
                'click',
                function () {

                    showZone(this);

                }
            );

        }
    );

    if (close) {

        close.addEventListener(
            'click',
            function () {

                panel.hidden = true;

                markers.forEach(
                    function (marker) {

                        marker.classList.remove(
                            'zone-focused'
                        );

                    }
                );

            }
        );

    }

    render();

})();


/* ============================================================
   GLOBAL MINE SELECTOR
   ============================================================ */

(function () {

    const button = document.getElementById('mineSelectorButton');
    const menu = document.getElementById('mineSelectorMenu');

    if (!button || !menu) {
        return;
    }

    function closeMenu() {
        menu.hidden = true;
        button.setAttribute('aria-expanded', 'false');
    }

    button.addEventListener('click', function (event) {
        event.stopPropagation();
        const willOpen = menu.hidden;
        menu.hidden = !willOpen;
        button.setAttribute('aria-expanded', String(willOpen));
    });

    menu.addEventListener('click', function (event) {
        if (event.target.closest('a')) {
            closeMenu();
        }
    });

    document.addEventListener('click', function (event) {
        if (!event.target.closest('.mine-select-wrap')) {
            closeMenu();
        }
    });

    document.addEventListener('keydown', function (event) {
        if (event.key === 'Escape') {
            closeMenu();
        }
    });

})();
