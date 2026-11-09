# Orb graph

A 3D force-directed node graph with glowing orbs, colored by node type, on a dark background.

## Run it

Requires Node.js 16 or newer. There is nothing to install.

    node server.js

Then open http://localhost:3000 (use `PORT=8080 node server.js` for another port).

## Use it

- Drag an orb to move it. Click an orb to focus its links. Click empty space or press Esc to clear.
- Use the 2D and 3D buttons at the top to switch views. 2D flattens the graph onto a plane that faces you; orbit to look at it from other angles.
- The buttons at the bottom right zoom in, zoom out, and fit all nodes on screen.
- Click a type in the legend to hide or show it.

## Use your own data

The app currently uses built-in fake data. To load `data/graph.json` instead, set `USE_FAKE_DATA = false` near the top of `public/app.js`.


Edit `data/graph.json` and refresh the page:

    { "nodes": [ { "id": "Auth", "type": "service" } ],
      "links": [ { "source": "Auth", "target": "Postgres" } ] }

Each node's `type` sets its color. Known types: service, database, person, concept, file.
Any other type name gets its own color automatically. To pick colors, edit `PALETTE` at the top of `public/app.js`.
