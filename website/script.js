const tabs = document.querySelectorAll(".tab");
const preview = document.querySelector("#screenPreview");
const storeProductId = document.body.dataset.storeProductId?.trim();
const storeBadge = document.querySelector("#microsoftStoreBadge");
const storeBadgeWrap = document.querySelector(".store-badge-wrap");
const storePlaceholder = document.querySelector("#storePlaceholder");

tabs.forEach((tab) => {
  tab.addEventListener("click", () => {
    const nextShot = tab.dataset.shot;

    tabs.forEach((item) => {
      item.classList.remove("is-active");
      item.setAttribute("aria-selected", "false");
    });

    tab.classList.add("is-active");
    tab.setAttribute("aria-selected", "true");
    preview.src = nextShot;
  });
});

if (storeProductId && storeBadge && storeBadgeWrap && storePlaceholder) {
  storeBadge.setAttribute("productid", storeProductId);
  storeBadgeWrap.hidden = false;
  storePlaceholder.hidden = true;
}
