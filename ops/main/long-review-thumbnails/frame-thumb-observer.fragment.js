// A long concert can contain hundreds of shots. Fetch private JPEGs only
// when their cards approach the viewport, never 300+ at once.
const frameThumbObserver = typeof IntersectionObserver === 'function'
  ? new IntersectionObserver(entries => {
      for (const entry of entries) {
        if (!entry.isIntersecting) continue;
        const img=entry.target;
        frameThumbObserver.unobserve(img);
        if (img.dataset.reviewThumbnail) img.src=img.dataset.reviewThumbnail;
      }
    },{rootMargin:'250px 0px'}) : null;
