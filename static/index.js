const express = require('express');
const path = require('path');
const { Client } = require('@notionhq/client');
const cors = require('cors');
require('dotenv').config();

const port = process.env.PORT || 3000;
const DATABASE_ID = process.env.DATABASE_ID;
const app = express();
const maxDuration = 60;

app.use(cors());
app.use(express.json())

app.use(express.static(path.join(__dirname, '../public')));


app.get('/', (req, res) => {
  res.sendFile(path.join(__dirname, '../public', 'index.html'));
});

const notion = new Client({ 
    auth: process.env.API_KEY,
});


app.get('/getRecords', async (req, res) => {
  let allRecords = [];
  let nextPageToken = undefined;
  try {
      do {
        const response = await notion.databases.query({
          database_id: DATABASE_ID,
          start_cursor: nextPageToken,
          // filter by status Active, Unresponsive, Joined
          filter: {
            or: [
              {
                property: "Status", 
                status: {
                  equals: "Active" 
                }
              },
              {
                property: "Status", 
                status: {
                  equals: "Unresponsive" 
                }
              },
              // {
              //   property: "Status", 
              //   status: {
              //     equals: "Joined"
              //   }
              // },
              
            ],
          },
        });
  
        allRecords.push(...response.results);
  
        nextPageToken = response.next_cursor;
      } while (nextPageToken);

      // remove empty records
      allRecords = allRecords.filter(record => record.properties.Name.title[0]?.plain_text !== undefined);
      const formattedRecords = allRecords.map(record => ({
        id: record.properties.ID.unique_id.number,
        name: record.properties.Name.title[0]?.plain_text || '',
        hours: record.properties["Total Hours"].formula.number || 0,
      }));
      const realFormattedRecords = formattedRecords.filter(record => record.hours > 50 && record.hours < 100);
      realFormattedRecords.sort((a, b) => (a.hours > b.hours) ? 1 : -1);
      res.status(200).json(realFormattedRecords);
    } catch (error) {
      console.error('Error fetching database records:', error);
      res.status(500).json({ error: 'Internal server error' }); // Set HTTP status code to 500 (Internal Server Error) for any unexpected errors
    }
});

app.get('/getRecords50', async (req, res) => {
  let allRecords = [];
  let nextPageToken = undefined;
  try {
      do {
        const response = await notion.databases.query({
          database_id: DATABASE_ID,
          start_cursor: nextPageToken,
          // filter by status Active, Unresponsive, Joined
          filter: {
            or: [
              {
                property: "Status", 
                status: {
                  equals: "Active" 
                }
              },
              {
                property: "Status", 
                status: {
                  equals: "Unresponsive" 
                }
              },
              // {
              //   property: "Status", 
              //   status: {
              //     equals: "Joined"
              //   }
              // },
              
            ],
          },
        });
  
        allRecords.push(...response.results);
  
        nextPageToken = response.next_cursor;
      } while (nextPageToken);

      // remove empty records
      allRecords = allRecords.filter(record => record.properties.Name.title[0]?.plain_text !== undefined);
      const formattedRecords = allRecords.map(record => ({
        id: record.properties.ID.unique_id.number,
        name: record.properties.Name.title[0]?.plain_text || '',
        hours: record.properties["Total Hours"].formula.number || 0,
      }));
      const realFormattedRecords = formattedRecords.filter(record => record.hours >= 50 && record.hours < 100);
      realFormattedRecords.sort((a, b) => (a.hours > b.hours) ? 1 : -1);
      res.status(200).json(realFormattedRecords);
    } catch (error) {
      console.error('Error fetching database records:', error);
      res.status(500).json({ error: 'Internal server error' }); // Set HTTP status code to 500 (Internal Server Error) for any unexpected errors
    }
});

app.get('/getRecords100', async (req, res) => {
  let allRecords = [];
  let nextPageToken = undefined;
  try {
      do {
        const response = await notion.databases.query({
          database_id: DATABASE_ID,
          start_cursor: nextPageToken,
          // filter by status Active, Unresponsive, Joined
          filter: {
            or: [
              {
                property: "Status", 
                status: {
                  equals: "Active" 
                }
              },
              {
                property: "Status", 
                status: {
                  equals: "Unresponsive" 
                }
              },
              // {
              //   property: "Status", 
              //   status: {
              //     equals: "Joined"
              //   }
              // },
              
            ],
          },
        });
  
        allRecords.push(...response.results);
  
        nextPageToken = response.next_cursor;
      } while (nextPageToken);

      // remove empty records
      allRecords = allRecords.filter(record => record.properties.Name.title[0]?.plain_text !== undefined);
      const formattedRecords = allRecords.map(record => ({
        id: record.properties.ID.unique_id.number,
        name: record.properties.Name.title[0]?.plain_text || '',
        hours: record.properties["Total Hours"].formula.number || 0,
      }));
      const realFormattedRecords = formattedRecords.filter(record => record.hours >= 100 && record.hours < 150);
      realFormattedRecords.sort((a, b) => (a.hours > b.hours) ? 1 : -1);
      res.status(200).json(realFormattedRecords);
    } catch (error) {
      console.error('Error fetching database records:', error);
      res.status(500).json({ error: 'Internal server error' }); // Set HTTP status code to 500 (Internal Server Error) for any unexpected errors
    }
});

app.get('/getAccepted', async (req, res) => {
  let allRecords = [];
  let nextPageToken = undefined;
  try {
      do {
        const response = await notion.databases.query({
          database_id: DATABASE_ID,
          start_cursor: nextPageToken,
          // filter by status Active, Unresponsive, Joined
          filter: {
            or: [
              {
                property: "Status", 
                status: {
                  equals: "Accepted" 
                },
              },
              {
                property: "Status", 
                status: {
                  equals: "Accepted / Pending Email" 
                }
              }
            ],
          },
        });
  
        allRecords.push(...response.results);
  
        nextPageToken = response.next_cursor;
      } while (nextPageToken);
      allRecords = allRecords.filter(record => record.properties.Name.title[0]?.plain_text !== undefined);
      
      const formattedRecords = allRecords.map(record => ({
        name: record.properties.Name.title[0]?.plain_text || '',
        email: record.properties.Email.email || '',
      }));
      formattedRecords.sort((a, b) => (a.name > b.name) ? 1 : -1);
      res.status(200).json(formattedRecords);

    } catch (error) {
      console.error('Error fetching accepted records:', error);
      res.status(500).json({ error: 'Internal server error' }); // Set HTTP status code to 500 (Internal Server Error) for any unexpected errors
    }
  }

)

app.post('/moveAccepted', async (req, res) => {
  const acceptedList = req.body;
  try {
    acceptedList.forEach(async (obj) => {
      const filterEmail = obj.email;
      const filterResponse = await notion.databases.query({
        database_id: DATABASE_ID,
        filter: {
          property: 'Email', 
          rich_text: {
            equals: filterEmail,
          },
        },
      });
      record = filterResponse.results[0];
      if (record.properties.Status.status.name !== "Accepted / Pending Email") {
        console.log(`Record ${obj.name} already moved`);
      }
      else {
        const existingPageId = record.id;
        const updateResponse = await notion.pages.update({
          page_id: existingPageId,
          properties: {
            Status: {
              status: {
                name: 'Acceptance Sent',
              },
            },
          },
        });
      }
    });
    res.status(200).json({ message: 'Accepted records moved successfully' });
  }
  catch (error) {
    console.error('Error moving accepted records:', error);
    res.status(500).json({ error: 'Internal server error' }); // Set HTTP status code to 500 (Internal Server Error) for any unexpected errors
  }
  
});

app.post('/submitTimes', async (req, res) => {
    // get json data from req
    // send to notion
    // send back response
    const timeData = req.body;
    console.log(timeData);
    
    const SundaySlots = {multi_select: timeData.sunday.map((slot) => ({name: slot,})),};
    const MondaySlots = {multi_select: timeData.monday.map((slot) => ({name: slot,})),};
    const TuesdaySlots = {multi_select: timeData.tuesday.map((slot) => ({name: slot,})),};
    const WednesdaySlots = {multi_select: timeData.wednesday.map((slot) => ({name: slot,})),};
    const ThursdaySlots = {multi_select: timeData.thursday.map((slot) => ({name: slot,})),};
    const FridaySlots = {multi_select: timeData.friday.map((slot) => ({name: slot,})),};
    const SaturdaySlots = {multi_select: timeData.saturday.map((slot) => ({name: slot,})),};

    const filterEmail = timeData.email;

    // Check if a page with the same email already exists
    const filterResponse = await notion.databases.query({
      database_id: DATABASE_ID,
      filter: {
        property: 'Email', 
        rich_text: {
          equals: filterEmail,
        },
      },
    });

    if (filterResponse.results.length > 0) {
      // If a page with the same email exists, update it
      const existingPageId = filterResponse.results[0].id;
      
      const updateResponse = await notion.pages.update({
        page_id: existingPageId,
        properties: {
          // Update the properties you want to change
          Monday: MondaySlots,
          Tuesday: TuesdaySlots,
          Wednesday: WednesdaySlots,
          Thursday: ThursdaySlots,
          Friday: FridaySlots,
          Saturday: SaturdaySlots,
          Sunday: SundaySlots,
        },
      });

      res.send(updateResponse);
    }
    else{
      res.status(400).send({error:"Email not found"});
    } 
});


app.listen(port, () => {
    console.log(`Server started on port ${port}`)
});

module.exports = app;