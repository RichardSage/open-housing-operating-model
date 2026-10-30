# How to add to the Open Housing Operating Model

A step-by-step guide for first-time contributors. **You don't need to be technical.** The easiest way to contribute is to fill in a short form, and someone who maintains the model will make the change for you.

## The easy way: suggest a change (about 5 minutes)

1. **Find where your idea fits.** Open the [atlas](https://richardsage.github.io/open-housing-operating-model/) and find the closest service, such as "Repair my home", or the closest function area, such as "Responsive Repairs".
2. **Click "Suggest a change"** on that service or area. The form opens with that part of the model already filled in. You can also start from the [blank form](https://github.com/RichardSage/open-housing-operating-model/issues/new/choose).
3. **Sign in to GitHub.** If you don't have an account, creating one is free and takes a couple of minutes at [github.com](https://github.com/signup). You only need an email address.
4. **Fill in the form:**
   - **What kind of change?** For example, adding something, renaming something or moving something.
   - **Where?** This is usually already filled in.
   - **What should change?** Be specific. For example: "Add 'Report a broken lift' as a request under Repair my home".
   - **Why?** Explain what's missing or wrong. A link to regulation, guidance or your own experience helps.
5. **Click "Submit new issue".** That's it.

**What happens next:** your suggestion appears publicly so others can comment. A maintainer reviews it. If it's agreed, it's added to the model and the atlas updates. Your contribution is credited.

## Tips for a good suggestion

- **Use residents' words for services**, for example "Report a broken lift" rather than "Lift breakdown management".
- **Start activities with a verb**, for example "Inspect fire doors".
- **Think about whether it's true for most housing associations**, not just yours.
- **One idea per suggestion** makes it easier to discuss and agree.

## The hands-on way: edit it yourself

Once you're comfortable, you can make a change directly:

1. On the [repository](https://github.com/RichardSage/open-housing-operating-model), open the `model` folder.
   - Services are in `services.yaml`.
   - The operating model has one file per area in `function-areas`.
2. Click the **pencil icon** to edit.
3. **Copy an existing block and change the words.** Keep the spacing exactly the same, because the indentation matters. Give your new item the next unused number.
4. Click **Commit changes**, then **Propose changes**. GitHub creates a "pull request", which is a proposal for review.
5. **An automatic check runs.**
   - A green tick means everything fits together.
   - A red cross means something's wrong, and the check explains what in plain English.
6. A maintainer reviews and merges it.

For naming rules, how codes work and the full file format, see [CONTRIBUTING.md](CONTRIBUTING.md).

## Bigger ideas

For larger ideas, such as a version for Scotland or Wales, services for councils and contractors, or a new layer on top of the model, start a conversation in [Discussions](https://github.com/RichardSage/open-housing-operating-model/discussions).
