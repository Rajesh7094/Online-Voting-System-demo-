# 🗳️ Online Voting System - Messi vs Ronaldo

A comprehensive web-based voting application built with Streamlit that allows students to vote for their favorite football GOAT (Greatest Of All Time) - Lionel Messi or Cristiano Ronaldo.

## ✨ Features

### 👥 Student Features
- **Student Registration** - Secure signup with unique register numbers
- **Vote Casting** - Simple and intuitive voting interface
- **Vote Verification** - Prevents duplicate voting per student
- **Real-time Feedback** - Instant confirmation after voting

### 👨‍💼 Admin Features
- **Comprehensive Dashboard** - Multi-tab admin panel
- **Real-time Results** - Live vote counting and visualization
- **Student Management** - View all registered students
- **Voting Analytics** - Detailed insights on voting patterns
- **Winner Declaration** - Official winner announcement system
- **Re-election Management** - One-click election reset functionality
- **Data Export** - CSV export for record keeping

### 🎨 Visual Features
- **Candidate Photos** - Local image support with smart fallbacks
- **Interactive Charts** - Bar charts and pie charts for results
- **Responsive Design** - Works on desktop and mobile devices
- **Celebration Effects** - Balloons animation after voting

## 🚀 Quick Start

### Prerequisites
- Python 3.7+
- pip package manager

### Installation

1. **Clone or download the project**
   ```bash
   git clone <repository-url>
   cd online-voting-system
   ```

2. **Install required packages**
   ```bash
   pip install streamlit sqlite3 pandas plotly Pillow
   ```

3. **Set up candidate images** (Optional but recommended)
   ```bash
   mkdir images
   ```
   Add your candidate photos:
   - `images/messi.jpg`
   - `images/ronaldo.jpg`

4. **Run the application**
   ```bash
   streamlit run app.py
   ```

5. **Access the application**
   Open your browser and go to: `http://localhost:8501`

## 📁 Project Structure

```
online-voting-system/
├── app.py                 # Main application file
├── images/                # Candidate photos directory
│   ├── messi.jpg         # Messi's photo
│   └── ronaldo.jpg       # Ronaldo's photo
├── voting_system.db      # SQLite database (auto-created)
├── README.md             # Project documentation
└── requirements.txt      # Python dependencies
```

## 🗄️ Database Schema

The application uses SQLite with two main tables:

### Students Table
| Column | Type | Description |
|--------|------|-------------|
| register_number | TEXT (PRIMARY KEY) | Unique student identifier |
| name | TEXT | Student's full name |
| registration_time | TIMESTAMP | Registration timestamp |

### Votes Table
| Column | Type | Description |
|--------|------|-------------|
| id | INTEGER (PRIMARY KEY) | Auto-increment vote ID |
| register_number | TEXT (FOREIGN KEY) | References students table |
| candidate | TEXT | Voted candidate (Messi/Ronaldo) |
| vote_time | TIMESTAMP | Vote timestamp |

## 🎮 How to Use

### For Students

1. **Registration**
   - Click "Student Sign-Up" on homepage
   - Enter unique register number and full name
   - Complete registration

2. **Voting**
   - Click "Vote Now" on homepage
   - Verify with your register number
   - Select your candidate (Messi or Ronaldo)
   - Confirm your vote

### For Administrators

1. **Login**
   - Click "Admin Panel" on homepage
   - Use credentials: `admin` / `admin123`

2. **Admin Dashboard Tabs**
   - **📊 Voting Results** - Real-time vote counts and charts
   - **👥 Student Data** - All registered students and voting status
   - **✅ Voted Students** - Detailed voting records
   - **🏆 Declare Winner** - Official winner announcement
   - **🔄 Re-Election** - Reset system for new elections

## 🔧 Configuration

### Admin Credentials
Default admin login (change in production):
- Username: `admin`
- Password: `admin123`

### Supported Image Formats
- `.jpg` / `.jpeg`
- `.png`

### Image Naming Convention
- Messi: `messi.jpg`, `messi.jpeg`, or `messi.png`
- Ronaldo: `ronaldo.jpg`, `ronaldo.jpeg`, or `ronaldo.png`

## 📊 Technical Features

### Security
- ✅ Duplicate vote prevention
- ✅ Student registration validation
- ✅ Admin authentication
- ✅ SQL injection protection

### Data Management
- ✅ SQLite database with ACID properties
- ✅ Automatic database initialization
- ✅ Foreign key relationships
- ✅ Transaction safety

### User Experience
- ✅ Responsive design
- ✅ Real-time updates
- ✅ Error handling and validation
- ✅ Visual feedback and animations

## 🎨 Customization

### Adding New Candidates
1. Modify the candidate options in voting functions
2. Update image loading functions
3. Adjust database schema if needed

### Changing Colors/Theme
1. Update CSS in display functions
2. Modify Plotly chart color schemes
3. Adjust placeholder gradient colors

### Extending Functionality
- Add more detailed analytics
- Implement email notifications
- Add vote scheduling features
- Include demographic analysis

## 🚀 Deployment Options

### Local Development
```bash
streamlit run app.py
```

### Streamlit Cloud
1. Push code to GitHub repository
2. Connect to Streamlit Cloud
3. Deploy directly from GitHub

### Docker (Optional)
```dockerfile
FROM python:3.9-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

EXPOSE 8501

CMD ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]
```

## 📋 Requirements.txt

```txt
streamlit==1.28.1
pandas==2.1.1
plotly==5.17.0
Pillow==10.0.1
```

## 🛠️ Troubleshooting

### Common Issues

**Images not displaying:**
- Check file names match exactly (`messi.jpg`, `ronaldo.jpg`)
- Ensure images are in `images/` folder
- Verify file permissions

**Database errors:**
- Delete `voting_system.db` to reset
- Check write permissions in project directory

**Streamlit issues:**
- Update Streamlit: `pip install --upgrade streamlit`
- Clear cache: Delete `.streamlit/` folder

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## 📝 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🙏 Acknowledgments

- Built with [Streamlit](https://streamlit.io/)
- Charts powered by [Plotly](https://plotly.com/)
- Database: SQLite
- Image processing: PIL (Pillow)

## 📞 Support

For support and questions:
- Create an issue in the repository
- Check the troubleshooting section
- Review the setup guide

---

**Made with ❤️ for football fans worldwide! ⚽**

**Vote for your GOAT: Messi 🐐 or Ronaldo 🐐**