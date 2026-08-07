(() => {
  const root = document.documentElement;
  const gsap = window.gsap;
  const ScrollTrigger = window.ScrollTrigger;
  if (!gsap || !ScrollTrigger) {
    root.dataset.motionReady = "false";
    return;
  }

  gsap.registerPlugin(ScrollTrigger);
  const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  root.dataset.motionMode = reduceMotion ? "reduced" : "full";

  const revealTargets = [
    ...document.querySelectorAll(
      ".site-header .brand, .primary-nav, .header-status, .history-quickbar > *, " +
      "#parser .intro-rule, #parser .intro-grid, #parser-view .parser-stage .stage-heading, #parser-form, " +
      "#parser-view .lower-rail"
    ),
  ];
  revealTargets.forEach((element) => element.setAttribute("data-motion-reveal", ""));

  const markAnimating = (targets) => {
    gsap.utils.toArray(targets).forEach((element) => element?.classList.add("is-motion-animating"));
  };
  const clearAnimating = (targets) => {
    const elements = gsap.utils.toArray(targets).filter(Boolean);
    elements.forEach((element) => element.classList.remove("is-motion-animating"));
    gsap.set(elements, { clearProps: "transform,opacity,visibility" });
  };

  const toggleTranscript = (transcript, expand) => {
    if (!transcript) return;
    gsap.killTweensOf(transcript);
    if (reduceMotion) {
      transcript.classList.toggle("is-collapsed", !expand);
      transcript.dataset.motionTranscript = expand ? "expanded" : "collapsed";
      ScrollTrigger.refresh();
      return;
    }

    const styles = getComputedStyle(transcript);
    const collapsedHeight = Number.parseFloat(styles.lineHeight) * 7
      + Number.parseFloat(styles.paddingTop)
      + Number.parseFloat(styles.paddingBottom);
    const startHeight = transcript.getBoundingClientRect().height;
    transcript.classList.add("is-motion-animating");
    transcript.dataset.motionTranscript = expand ? "expanding" : "collapsing";
    transcript.classList.toggle("is-collapsed", !expand);
    gsap.set(transcript, { maxHeight: startHeight, overflow: "hidden" });
    gsap.to(transcript, {
      maxHeight: expand ? transcript.scrollHeight : collapsedHeight,
      duration: expand ? 0.48 : 0.38,
      ease: "power3.inOut",
      overwrite: "auto",
      onComplete: () => {
        transcript.classList.toggle("is-collapsed", !expand);
        transcript.dataset.motionTranscript = expand ? "expanded" : "collapsed";
        transcript.classList.remove("is-motion-animating");
        gsap.set(transcript, { clearProps: "maxHeight,overflow" });
        ScrollTrigger.refresh();
      },
    });
  };

  const boundElements = new WeakSet();
  const interactiveSelector = [
    ".choice-card",
    ".module-choice",
    ".recommend-card",
    ".history-item",
    ".note-history-list article",
    ".recovery-list article",
    ".export-choice",
  ].join(",");

  function bindMicroInteractions(scope = document) {
    const elements = [];
    if (scope instanceof Element && scope.matches(interactiveSelector)) elements.push(scope);
    elements.push(...scope.querySelectorAll(interactiveSelector));
    elements.forEach((element) => {
      if (boundElements.has(element)) return;
      boundElements.add(element);
      element.dataset.motionBound = "true";
      if (reduceMotion) return;
      element.addEventListener("pointerenter", () => {
        element.classList.add("is-motion-animating");
        gsap.to(element, { y: -3, duration: 0.2, ease: "power2.out", overwrite: "auto" });
      });
      element.addEventListener("pointerleave", () => {
        gsap.to(element, {
          y: 0,
          duration: 0.22,
          ease: "power2.out",
          overwrite: "auto",
          clearProps: "transform",
          onComplete: () => element.classList.remove("is-motion-animating"),
        });
      });
    });

    scope.querySelectorAll(".history-shortcut, .button-primary").forEach((button) => {
      if (boundElements.has(button)) return;
      boundElements.add(button);
      button.dataset.motionBound = "true";
      const arrow = button.matches(".history-shortcut")
        ? button.querySelector(".history-shortcut__arrow")
        : button.querySelector(":scope > span:last-child");
      if (!arrow || reduceMotion) return;
      button.addEventListener("pointerenter", () => {
        gsap.to(arrow, { x: button.matches(".history-shortcut") ? 7 : 5, duration: 0.18, ease: "power2.out", overwrite: "auto" });
      });
      button.addEventListener("pointerleave", () => {
        gsap.to(arrow, { x: 0, duration: 0.2, ease: "power2.out", overwrite: "auto", clearProps: "transform" });
      });
    });
  }

  function animateWelcome(dialog, opening, onComplete) {
    const frame = dialog?.querySelector("[data-welcome-frame]");
    if (!frame) {
      onComplete?.();
      return null;
    }
    const items = [...frame.querySelectorAll("[data-welcome-reveal]")];
    gsap.killTweensOf([frame, ...items]);
    if (reduceMotion) {
      clearAnimating([frame, ...items]);
      onComplete?.();
      return null;
    }
    markAnimating([frame, ...items]);
    if (!opening) {
      return gsap.to(frame, {
        y: -10,
        scale: 0.985,
        autoAlpha: 0,
        duration: 0.2,
        ease: "power2.in",
        overwrite: "auto",
        onComplete: () => {
          clearAnimating([frame, ...items]);
          onComplete?.();
        },
      });
    }
    const timeline = gsap.timeline({
      defaults: { ease: "power3.out" },
      onComplete: () => clearAnimating([frame, ...items]),
    });
    timeline.fromTo(frame, { y: 24, scale: 0.985, autoAlpha: 0 }, {
      y: 0, scale: 1, autoAlpha: 1, duration: 0.38,
    });
    timeline.fromTo(items, { y: 12, autoAlpha: 0 }, {
      y: 0, autoAlpha: 1, duration: 0.3, stagger: 0.055,
    }, 0.1);
    return timeline;
  }

  const stateItemSelector = [
    ".source-ready-banner", ".notes-ready-card", ".notes-request-card",
    ".analysis-top", ".analysis-steps li", ".analysis-source",
    ".recommendation-banner", ".note-title-card", ".recommendation-grid > *", ".transcript-drawer", ".recommendation-actions",
    ".custom-intro", ".settings-stack > *", ".other-requirement", ".custom-actions",
    ".stale-warning", ".stale-editor", ".generation-stack > *", ".semantic-progress li",
    ".outline-stack > *", ".outline-list > li", ".chapter-generation-stack > *", ".chapter-list li",
    ".chapter-failure-stack > *", ".recovery-list article", ".generation-complete-stack > *", ".completion-grid > *",
    ".reader-command-bar", ".note-document-header", ".note-toc", ".note-summary", ".note-chapter", ".note-version-footer",
    ".editor-toolbar", ".candidate-stack > *", ".export-stack > *", ".omission-stack > *",
    ".note-history-list article", ".history-item",
  ].join(",");
  let readingTriggers = [];

  function clearReadingTriggers() {
    readingTriggers.forEach((trigger) => trigger.kill());
    readingTriggers = [];
  }

  function installReadingReveals(element) {
    clearReadingTriggers();
    if (reduceMotion) return;
    element.querySelectorAll(".note-chapter").forEach((chapter, index) => {
      const trigger = ScrollTrigger.create({
        id: `note-chapter-reveal-${index}`,
        trigger: chapter,
        start: "clamp(top 92%)",
        once: true,
        onEnter: () => {
          chapter.classList.add("is-motion-animating");
          gsap.fromTo(chapter, { y: 16, autoAlpha: 0 }, {
            y: 0,
            autoAlpha: 1,
            duration: 0.46,
            ease: "power2.out",
            clearProps: "transform,opacity,visibility",
            onComplete: () => chapter.classList.remove("is-motion-animating"),
          });
        },
      });
      readingTriggers.push(trigger);
    });
  }

  function animateState(element) {
    if (!(element instanceof HTMLElement)) return;
    clearReadingTriggers();
    bindMicroInteractions(element);
    const items = [...element.querySelectorAll(stateItemSelector)];
    items.forEach((item) => item.dataset.motionItem = "true");
    const isPublicDemoNote = document.body.classList.contains("public-demo-active")
      && (element.matches(".note-reading-stack") || Boolean(element.querySelector(".note-reading-stack")));
    element.dataset.motionState = reduceMotion || isPublicDemoNote ? "settled" : "entering";
    if (reduceMotion || isPublicDemoNote) {
      clearAnimating([element, ...items]);
      ScrollTrigger.refresh();
      return;
    }

    markAnimating([element, ...items]);
    const timeline = gsap.timeline({
      defaults: { ease: "power2.out" },
      onComplete: () => {
        clearAnimating([element, ...items]);
        element.dataset.motionState = "settled";
        installReadingReveals(element);
        ScrollTrigger.refresh();
      },
    });
    timeline.fromTo(element, { y: 16, autoAlpha: 0, scale: 0.994 }, {
      y: 0, autoAlpha: 1, scale: 1, duration: 0.38,
    });
    if (items.length) {
      timeline.fromTo(items, { y: 12, autoAlpha: 0 }, {
        y: 0, autoAlpha: 1, duration: 0.32, stagger: 0.035,
      }, 0.1);
    }
  }

  function animateView(view) {
    if (!(view instanceof HTMLElement) || view.hidden) return;
    view.dataset.motionView = reduceMotion ? "settled" : "entering";
    if (reduceMotion) {
      clearAnimating(view);
      return;
    }
    view.classList.add("is-motion-animating");
    gsap.fromTo(view, { x: 14, autoAlpha: 0 }, {
      x: 0,
      autoAlpha: 1,
      duration: 0.36,
      ease: "power3.out",
      overwrite: "auto",
      clearProps: "transform,opacity,visibility",
      onComplete: () => {
        view.classList.remove("is-motion-animating");
        view.dataset.motionView = "settled";
        ScrollTrigger.refresh();
      },
    });
  }

  [document.querySelector("#state-host"), document.querySelector("#notes-state-host")].filter(Boolean).forEach((host) => {
    new MutationObserver((mutations) => {
      mutations.forEach((mutation) => mutation.addedNodes.forEach(animateState));
    }).observe(host, { childList: true });
  });
  [document.querySelector("#parser-view"), document.querySelector("#notes-view")].filter(Boolean).forEach((view) => {
    new MutationObserver(() => animateView(view)).observe(view, { attributes: true, attributeFilter: ["hidden"] });
  });

  bindMicroInteractions(document);

  const parserForm = document.querySelector("#parser-form");
  const platformDetection = parserForm?.querySelector("#platform-detection");
  if (parserForm) {
    parserForm.dataset.motionFocus = "idle";
    parserForm.addEventListener("focusin", () => {
      parserForm.dataset.motionFocus = "active";
      if (reduceMotion) return;
      parserForm.classList.add("is-motion-animating");
      gsap.to(parserForm, { y: -4, duration: 0.22, ease: "power2.out", overwrite: "auto" });
      gsap.to(platformDetection, { x: 4, duration: 0.24, ease: "power2.out", overwrite: "auto" });
    });
    parserForm.addEventListener("focusout", (event) => {
      if (parserForm.contains(event.relatedTarget)) return;
      parserForm.dataset.motionFocus = "idle";
      if (reduceMotion) return;
      gsap.to(parserForm, { y: 0, duration: 0.24, ease: "power2.out", overwrite: "auto", clearProps: "transform", onComplete: () => parserForm.classList.remove("is-motion-animating") });
      gsap.to(platformDetection, { x: 0, duration: 0.22, ease: "power2.out", overwrite: "auto", clearProps: "transform" });
    });
  }

  if (reduceMotion) {
    gsap.set(revealTargets, { clearProps: "all" });
    root.dataset.motionReady = "true";
  } else {
    const headerTargets = [".site-header .brand", ".primary-nav", ".header-status"];
    const historyTargets = ".history-quickbar > *";
    const heroTargets = "#parser .intro-grid > *";
    const intakeTargets = ["#parser-view .parser-stage .stage-heading", "#parser-form"];
    const entranceTargets = [...headerTargets, historyTargets, "#parser .intro-rule", heroTargets, ...intakeTargets];
    markAnimating(entranceTargets);
    gsap.timeline({
      defaults: { ease: "power3.out" },
      onComplete: () => {
        clearAnimating(entranceTargets);
        root.dataset.motionReady = "true";
        ScrollTrigger.refresh();
      },
    })
      .from(headerTargets, { y: -14, autoAlpha: 0, duration: 0.42, stagger: 0.07 }, 0)
      .from(historyTargets, { y: -12, autoAlpha: 0, duration: 0.46, stagger: 0.06 }, 0.12)
      .from("#parser .intro-rule", { scaleX: 0, transformOrigin: "left center", duration: 0.48 }, 0.22)
      .from(heroTargets, { y: 30, autoAlpha: 0, duration: 0.64, stagger: 0.1 }, 0.28)
      .from(intakeTargets, { y: 22, autoAlpha: 0, duration: 0.5, stagger: 0.08 }, 0.48);

    const lowerRail = document.querySelector("#parser-view .lower-rail");
    if (lowerRail) {
      ScrollTrigger.create({
        id: "parser-reveal-0",
        trigger: lowerRail,
        start: "clamp(top 88%)",
        once: true,
        onEnter: () => {
          markAnimating(lowerRail);
          gsap.fromTo(lowerRail, { y: 22, autoAlpha: 0 }, {
            y: 0, autoAlpha: 1, duration: 0.56, ease: "power2.out",
            clearProps: "transform,opacity,visibility",
            onComplete: () => lowerRail.classList.remove("is-motion-animating"),
          });
        },
      });
    }
  }

  window.VTNMotion = {
    reduceMotion,
    refresh: () => ScrollTrigger.refresh(),
    animateState,
    animateView,
    bindMicroInteractions,
    toggleTranscript,
    animateWelcome,
  };
})();
