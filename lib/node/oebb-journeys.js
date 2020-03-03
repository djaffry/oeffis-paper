
const oebb = require('oebb');

const origin = process.argv[2];
const destination = process.argv[3];

oebb.journeys(origin, destination, { when: new Date(), results: 5})
    .then(res => console.log(JSON.stringify(res)))
    .catch(console.error);
