# Publishing this repository (one-off setup)

You can delete this file once you've finished.

1. **Create the repository.** On GitHub choose **New repository**, name it `open-housing-operating-model`, make it **Public**, and don't add a README or licence (they're already here).
2. **Upload the files.** Either drag the contents of this folder into the "uploading an existing file" page on GitHub, or from a terminal in this folder run:
   ```bash
   git init -b main
   git add .
   git commit -m "First public draft (v0.1.0)"
   git remote add origin https://github.com/YOUR-USERNAME/open-housing-operating-model.git
   git push -u origin main
   ```
   Note: the `.github` folder starts with a dot and can be hidden. Make sure it's uploaded, because it contains the forms and automatic checks.
3. **Turn on GitHub Pages.** Settings → Pages → Source: **GitHub Actions**. The atlas publishes automatically after the next push to `main` (or run "Build and publish atlas" from the Actions tab).
4. **Add the repository link.** Edit `model/meta.yaml` and set `repo_url` to your repository's address. This adds "Contribute on GitHub" and "Suggest a change" links to the atlas.
5. **Turn on Discussions.** Settings → General → Features → Discussions.
6. **Fill in the About panel.** Add a description, the Pages link as the website, and topics such as `social-housing`, `housing-associations`, `operating-model`, `open-data`.
7. **Protect `main` (recommended).** Settings → Branches → add a rule for `main` requiring a pull request and the "Validate model" check to pass.
8. **Publish the first release.** Releases → Draft a new release → tag `v0.1.0`. The CSV and JSON are attached automatically.
9. **Optional:** to get GitHub's licence badge, add the full CC BY 4.0 legal text as `LICENSE` (Add file → Create new file → name it `LICENSE` → Choose a licence template → Creative Commons Attribution 4.0).
10. **Optional:** connect the repository to [Zenodo](https://zenodo.org/) to get a citable DOI for each release.
