# Conference Presentations

A landing page for my conference sessions. Each presentation shows its date, conference, location, a short description, a link to the HTML demo, and a slides download when I share one. Presentations are grouped by year, newest first.

## How it works

- `index.html` is the landing page. It reads `data/conferences.json` and builds the list.
- Each demo lives in its own folder inside `presentations/`.
- To add a presentation, upload its folder, then fill out the **Add a presentation** form on the Issues tab. A GitHub Action adds it to the list and the page updates in a minute or two.

## One-time setup

1. Create a new **public** repository named `conferences`.
2. Upload everything from this folder into the repository. Two items start with a dot, `.github` and `.nojekyll`, so your computer may hide them. On a Mac press Command + Shift + Period in Finder to show them. On Windows choose View, Show, Hidden items. If GitHub will not take the `.github` folder, use **Add file, Create new file** instead. Type `.github/workflows/add-presentation.yml` as the file name (typing the slashes makes the folders), paste in the contents, and commit. Repeat for `.github/ISSUE_TEMPLATE/add-presentation.yml`, `.github/ISSUE_TEMPLATE/config.yml`, and `.github/scripts/add_presentation.py`.
3. In the repository, go to **Settings, Pages**. Under **Build and deployment**, set Source to **Deploy from a branch**, choose the `main` branch and the `/ (root)` folder, and save.
4. After a minute or two the page is live at `https://jenncoon.github.io/conferences/` (your GitHub username, then the repository name).
5. On your Google Site, add a link or button that points to that address.

## Adding a presentation

1. Choose a short folder name with lowercase letters and hyphens, for example `concept-checks`. Put the demo's `index.html` and any files it needs inside. If you are sharing slides, put that file in the same folder.
2. Open the `presentations` folder in GitHub, choose **Add file, Upload files**, drag the folder in, and commit.
3. Go to the **Issues** tab, choose **New issue**, then **Get started** next to **Add a presentation**. Fill it out and submit.
4. In a few seconds a comment appears on the issue confirming the change, and the issue closes. The page updates in a minute or two.

What to type in the two link boxes:

- **HTML demo:** the folder name, such as `concept-checks`. If the demo already lives somewhere else, paste its full web link instead, such as `https://jenncoon.github.io/Concept-Checks/`.
- **Slides file:** the file name inside the same folder, such as `slides.pptx`. A path like `other-folder/slides.pptx` or a full web link also works. Leave it blank when you are not sharing slides. The page shows the file type and size next to the download link.

If the form finds a problem, for example a date it cannot read, it tells you in a comment. Edit the issue and save, and it tries again.

## Fixing or removing a presentation

- **Fix:** open the original issue (look under **Closed** on the Issues tab), choose the three dots on the first post, then **Edit**, change the details, and save. The entry updates.
- **Remove:** open `data/conferences.json`, choose the pencil icon, delete that presentation's block (from its opening `{` to its closing `}`, and the comma next to it), and commit.

## Bringing in past presentations

You can submit the form once per past presentation, pasting the older GitHub Pages link in the HTML demo box. You do not need to move the older repositories right away. Move a demo into the `presentations` folder whenever you like, then edit its issue to use the folder name.

## Good to know

- Only issues opened by the repository owner are processed. Anyone else's issue is ignored.
- GitHub's browser upload accepts files up to 25 MB. For larger PowerPoint files, use GitHub Desktop, which allows files up to 100 MB.
- The page uses Georgia. Devices without Georgia, such as many Android phones, show their default serif font instead.
- The landing page was checked against WCAG 2.1 AA. Your individual demo pages need their own check.
