const express = require('express');
const app = express();
const  { engine } = require("express-handlebars");
const path = require('path');
const dir = __dirname

app.engine("html", engine({
    extname: ".html",
    defaultLayout: "master",
    layoutsDir: path.join(dir, "Templates"),
    helpers: {
        'formatDate': function(dateString) {
            if (!dateString) return "";
            const date = new Date(dateString);
            
            // Returns format: Feb 8, 2026, 4:00 PM
            return date.toLocaleString('en-US', { 
                month: 'short', 
                day: 'numeric', 
                year: 'numeric', 
                hour: '2-digit', 
                minute: '2-digit' 
            });
        }
    }
}));

app.set("view engine", "html");
app.set("views", path.join(dir, "Templates", "sites"));

app.use(express.json());
app.use(express.static(dir));

app.get("/", (req, res) => {
    res.render("Project");
})

app.listen(3000, () => console.log("Server Running @ http://localhost:3000"));